from __future__ import annotations

from insurance_copilot.services import (
    ClaimExtractionService,
    ConversationService,
    CoverageService,
    DatabaseService,
    DemoDataService,
    DispatchService,
    NotificationService,
    OpenAIService,
)
from insurance_copilot.state import SessionStore

database_service = DatabaseService()
data_service = DemoDataService(database_service)
conversation_service = ConversationService()
claim_extraction_service = ClaimExtractionService()
coverage_service = CoverageService(database_service)
dispatch_service = DispatchService(database_service)
notification_service = NotificationService(database_service)
openai_service = OpenAIService()
session_store = SessionStore()
