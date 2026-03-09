from __future__ import annotations

from datetime import UTC, datetime

from insurance_copilot.models import CoverageDecision, CustomerNotification, DispatchPlan


class NotificationService:
    def build_message(self, coverage: CoverageDecision, dispatch: DispatchPlan) -> CustomerNotification:
        if coverage.status != "covered":
            message = (
                "Insurance Co-Pilot update: your case needs manual review. "
                "An agent will contact you shortly with next steps."
            )
        else:
            benefits = ""
            if dispatch.ancillary_benefits:
                benefits = f" Additional support: {', '.join(dispatch.ancillary_benefits)}."
            message = (
                "Insurance Co-Pilot update: your claim is covered. "
                f"{dispatch.action_type.replace('_', ' ').title()} from {dispatch.provider_name} "
                f"({dispatch.garage_name}) ETA {dispatch.eta_minutes} minutes.{benefits}"
            )

        return CustomerNotification(
            message=message,
            timestamp=datetime.now(tz=UTC),
        )

