from __future__ import annotations

from datetime import UTC, datetime

from insurance_copilot.models import CoverageDecision, CustomerNotification, DispatchPlan
from insurance_copilot.services.database_service import DatabaseService


class NotificationService:
    def __init__(self, database_service: DatabaseService) -> None:
        self.database_service = database_service

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

    def deliver(
        self,
        *,
        session_id: str,
        customer_name: str | None,
        phone: str | None,
        coverage: CoverageDecision,
        dispatch: DispatchPlan,
    ) -> CustomerNotification:
        notification = self.build_message(coverage, dispatch)
        self.database_service.add_notification(
            session_id=session_id,
            customer_name=customer_name,
            phone=phone,
            coverage_status=coverage.status,
            message=notification.message,
            timestamp=notification.timestamp.isoformat(),
        )
        return notification
