from __future__ import annotations

from insurance_copilot.models import ClaimIntake, CoverageDecision
from insurance_copilot.services.demo_data_service import DemoDataService


class CoverageService:
    def __init__(self, data_service: DemoDataService) -> None:
        self.data_service = data_service

    def evaluate(self, claim: ClaimIntake) -> tuple[CoverageDecision, dict]:
        policy = self._find_policy(claim)
        if policy is None:
            return (
                CoverageDecision(
                    status="manual_review",
                    reason="No policy match found.",
                    customer_explanation="We could not verify policy details automatically.",
                    manual_review_required=True,
                    confidence=0.3,
                ),
                {},
            )

        if policy["status"] != "active":
            return (
                CoverageDecision(
                    status="not_covered",
                    reason="Policy is not active.",
                    customer_explanation="Your policy appears inactive. A human agent will contact you.",
                    manual_review_required=True,
                    confidence=0.95,
                ),
                policy,
            )

        if not policy["roadside_assistance"]:
            return (
                CoverageDecision(
                    status="not_covered",
                    reason="Roadside assistance is not included.",
                    customer_explanation="Roadside assistance is not included in this plan.",
                    confidence=0.95,
                ),
                policy,
            )

        location = claim.location or ""
        region = location.split(":")[0]
        if region and region not in policy["covered_regions"]:
            return (
                CoverageDecision(
                    status="not_covered",
                    reason=f"Region '{region}' is not covered.",
                    customer_explanation="This location is outside covered regions in your policy.",
                    confidence=0.9,
                ),
                policy,
            )

        if region in policy["exclusions"]:
            return (
                CoverageDecision(
                    status="not_covered",
                    reason=f"Region '{region}' is excluded.",
                    customer_explanation="Your policy excludes this case.",
                    confidence=0.9,
                ),
                policy,
            )

        return (
            CoverageDecision(
                status="covered",
                reason="Roadside assistance coverage checks passed.",
                customer_explanation="Your claim is covered and assistance will be dispatched.",
                confidence=0.9,
            ),
            policy,
        )

    def _find_policy(self, claim: ClaimIntake) -> dict | None:
        policies = self.data_service.policies()
        if claim.policy_reference:
            for policy in policies:
                if policy["policy_reference"] == claim.policy_reference:
                    return policy
        if claim.customer_name:
            for policy in policies:
                if policy["customer_name"].lower() == claim.customer_name.lower():
                    return policy
        return None

