from __future__ import annotations

from insurance_copilot.services import (
    ClaimExtractionService,
    ConversationService,
    CoverageService,
    DemoDataService,
    DispatchService,
    NotificationService,
)
from insurance_copilot.state import SessionStore

data_service = DemoDataService()
conversation_service = ConversationService()
claim_extraction_service = ClaimExtractionService()
coverage_service = CoverageService(data_service)
dispatch_service = DispatchService(data_service)
notification_service = NotificationService()
session_store = SessionStore()

