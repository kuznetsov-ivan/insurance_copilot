from __future__ import annotations

from math import hypot

from insurance_copilot.models import ClaimIntake, CoverageDecision, DispatchPlan
from insurance_copilot.services.demo_data_service import DemoDataService


class DispatchService:
    def __init__(self, data_service: DemoDataService) -> None:
        self.data_service = data_service

    def recommend(self, claim: ClaimIntake, coverage: CoverageDecision, policy: dict) -> DispatchPlan:
        if coverage.status != "covered":
            return DispatchPlan(
                action_type="manual_escalation",
                provider_name="Manual Review Desk",
                garage_name="N/A",
                eta_minutes=0,
                ancillary_benefits=[],
            )

        requires_tow = (claim.is_drivable is False) or claim.issue_type in {"engine_failure", "collision"}
        action_type = "tow_truck" if requires_tow else "repair_van"
        if action_type == "tow_truck" and not policy.get("tow_covered", False):
            action_type = "manual_escalation"
        if action_type == "repair_van" and not policy.get("repair_van_covered", False):
            action_type = "manual_escalation"

        if action_type == "manual_escalation":
            return DispatchPlan(
                action_type=action_type,
                provider_name="Manual Review Desk",
                garage_name="N/A",
                eta_minutes=0,
                ancillary_benefits=[],
            )

        best_provider = self._nearest_provider(action_type, claim.location or "")
        benefits = ["Taxi voucher"] if policy.get("rental_or_taxi_covered", False) else []
        return DispatchPlan(
            action_type=action_type,
            provider_name=best_provider["provider_name"],
            garage_name=best_provider["garage_name"],
            eta_minutes=self._eta_minutes(best_provider, claim.location or ""),
            ancillary_benefits=benefits,
        )

    def _nearest_provider(self, action_type: str, location: str) -> dict:
        target_lat, target_lon = self._parse_coords(location)
        providers = [p for p in self.data_service.providers() if action_type in p["capabilities"]]
        return min(
            providers,
            key=lambda p: hypot(target_lat - float(p["lat"]), target_lon - float(p["lon"])),
        )

    def _eta_minutes(self, provider: dict, location: str) -> int:
        target_lat, target_lon = self._parse_coords(location)
        distance = hypot(target_lat - float(provider["lat"]), target_lon - float(provider["lon"]))
        return max(12, int(distance * 350))

    def _parse_coords(self, location: str) -> tuple[float, float]:
        if ":" in location:
            _, coords = location.split(":", 1)
        else:
            coords = location
        if "," not in coords:
            return (40.74, -73.98)
        lat_str, lon_str = coords.split(",", 1)
        try:
            return float(lat_str.strip()), float(lon_str.strip())
        except ValueError:
            return (40.74, -73.98)

