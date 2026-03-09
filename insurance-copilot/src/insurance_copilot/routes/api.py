from __future__ import annotations

from fastapi import APIRouter

from insurance_copilot.dependencies import (
    claim_extraction_service,
    conversation_service,
    coverage_service,
    data_service,
    dispatch_service,
    notification_service,
    session_store,
)
from insurance_copilot.models import (
    EvaluateClaimRequest,
    EvaluateClaimResponse,
    ObserverState,
    TranscriptRequest,
    TranscriptResponse,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/transcript", response_model=TranscriptResponse)
def append_transcript(payload: TranscriptRequest) -> TranscriptResponse:
    session = session_store.get(payload.session_id)
    session.transcript = f"{session.transcript} {payload.chunk}".strip()
    claim = claim_extraction_service.extract(session.transcript)
    missing_fields = conversation_service.missing_fields(claim)
    return TranscriptResponse(
        session_id=payload.session_id,
        transcript=session.transcript,
        extracted_fields=claim.model_dump(exclude_none=True),
        missing_fields=missing_fields,
        next_prompt=conversation_service.next_prompt(claim),
    )


@router.post("/claims/evaluate", response_model=EvaluateClaimResponse)
def evaluate_claim(payload: EvaluateClaimRequest) -> EvaluateClaimResponse:
    session = session_store.get(payload.session_id)
    transcript = payload.transcript or session.transcript
    claim = payload.claim or claim_extraction_service.extract(transcript)
    coverage_decision, policy = coverage_service.evaluate(claim)
    dispatch_plan = dispatch_service.recommend(claim, coverage_decision, policy)
    customer_notification = notification_service.build_message(coverage_decision, dispatch_plan)
    session.notifications.append(customer_notification.message)

    observer_state = ObserverState(
        transcript=transcript,
        extracted_fields=claim.model_dump(exclude_none=True),
        coverage_decision=coverage_decision,
        dispatch_plan=dispatch_plan,
        audit_notes=[
            coverage_decision.reason,
            "Fallback rule-based extraction enabled.",
        ],
    )
    follow_up_questions = []
    if coverage_decision.manual_review_required:
        follow_up_questions.append("Confirm policy details with a human agent.")
    if conversation_service.missing_fields(claim):
        follow_up_questions.append("Some intake fields are incomplete.")

    return EvaluateClaimResponse(
        claim=claim,
        coverage_decision=coverage_decision,
        dispatch_plan=dispatch_plan,
        customer_notification=customer_notification,
        observer_state=observer_state,
        follow_up_questions=follow_up_questions,
    )


@router.get("/demo-scenarios")
def demo_scenarios() -> dict:
    return {
        "scenarios": data_service.scenarios(),
        "customers": data_service.customers(),
        "policies": data_service.policies(),
    }


@router.post("/reset")
def reset_session(session_id: str = "default") -> dict[str, str]:
    session_store.reset(session_id)
    return {"status": "ok", "session_id": session_id}

