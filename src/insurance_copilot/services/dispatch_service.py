from __future__ import annotations

from math import hypot

from insurance_copilot.models import ClaimIntake, CoverageDecision, DispatchPlan, ProviderCandidate
from insurance_copilot.services.database_service import DatabaseService


class DispatchService:
    def __init__(self, database_service: DatabaseService) -> None:
        self.database_service = database_service

    def recommend(
        self,
        claim: ClaimIntake,
        coverage: CoverageDecision,
        policy: dict,
        provider_rows: list[dict] | None = None,
        forced_action: str | None = None,
    ) -> tuple[DispatchPlan, list[ProviderCandidate]]:
        if coverage.status != "covered":
            return (
                DispatchPlan(
                    action_type="manual_escalation",
                    provider_name="Manual Review Desk",
                    garage_name="N/A",
                    eta_minutes=0,
                    ancillary_benefits=[],
                ),
                [],
            )

        requires_tow = (claim.is_drivable is False) or claim.issue_type in {"engine_failure", "collision"}
        action_type = forced_action or ("tow_truck" if requires_tow else "repair_van")
        if action_type == "tow_truck" and not policy.get("tow_covered", False):
            action_type = "manual_escalation"
        if action_type == "repair_van" and not policy.get("repair_van_covered", False):
            action_type = "manual_escalation"

        if action_type == "manual_escalation":
            return (
                DispatchPlan(
                    action_type=action_type,
                    provider_name="Manual Review Desk",
                    garage_name="N/A",
                    eta_minutes=0,
                    ancillary_benefits=[],
                ),
                [],
            )

        provider_candidates = self._ranked_providers(action_type, claim.location or "", provider_rows)
        best_provider = provider_candidates[0]
        benefits = ["Taxi voucher"] if policy.get("rental_or_taxi_covered", False) else []
        selected_candidates = [
            ProviderCandidate(**candidate, selected=index == 0)
            for index, candidate in enumerate(provider_candidates[:4])
        ]
        return (
            DispatchPlan(
                action_type=action_type,
                provider_name=best_provider["provider_name"],
                garage_name=best_provider["garage_name"],
                eta_minutes=best_provider["eta_minutes"],
                ancillary_benefits=benefits,
                provider_lat=best_provider["lat"],
                provider_lon=best_provider["lon"],
            ),
            selected_candidates,
        )

    def _ranked_providers(
        self,
        action_type: str,
        location: str,
        provider_rows: list[dict] | None = None,
    ) -> list[dict]:
        target_lat, target_lon = self._parse_coords(location)
        providers = provider_rows or self.database_service.providers_for_action(action_type)
        ranked = []
        for provider in providers:
            distance = hypot(target_lat - float(provider["lat"]), target_lon - float(provider["lon"]))
            ranked.append(
                {
                    **provider,
                    "eta_minutes": max(12, int(distance * 350)),
                    "distance_score": round(distance, 4),
                }
            )
        return sorted(ranked, key=lambda provider: provider["distance_score"])

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
