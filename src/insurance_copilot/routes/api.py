from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from insurance_copilot.dependencies import (
    claim_extraction_service,
    conversation_service,
    coverage_service,
    data_service,
    database_service,
    dispatch_service,
    notification_service,
    openai_service,
    session_store,
)
from insurance_copilot.models import (
    ClaimIntake,
    EvaluateClaimRequest,
    EvaluateClaimResponse,
    NotificationFeedResponse,
    NotificationRecord,
    ObserverState,
    PolicyMatch,
    TranscriptRequest,
    TranscriptResponse,
    VoiceTurnResponse,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/transcript", response_model=TranscriptResponse)
def append_transcript(payload: TranscriptRequest) -> TranscriptResponse:
    session = session_store.get(payload.session_id)
    session.transcript = f"{session.transcript} {payload.chunk}".strip()
    claim, assistant_source = _extract_claim(session.transcript)
    missing_fields = conversation_service.missing_fields(claim)
    return TranscriptResponse(
        session_id=payload.session_id,
        transcript=session.transcript,
        extracted_fields=claim.model_dump(exclude_none=True),
        missing_fields=missing_fields,
        next_prompt=conversation_service.next_prompt(claim),
        assistant_source=assistant_source,
    )


@router.post("/claims/evaluate", response_model=EvaluateClaimResponse)
def evaluate_claim(payload: EvaluateClaimRequest) -> EvaluateClaimResponse:
    session = session_store.get(payload.session_id)
    transcript = payload.transcript or session.transcript
    claim = payload.claim or _extract_claim(transcript)[0]
    coverage_decision, policy, coverage_query, decision_source = _evaluate_coverage(claim, transcript)
    dispatch_plan, provider_candidates, dispatch_query = _recommend_dispatch(claim, coverage_decision, policy)
    customer_notification = notification_service.deliver(
        session_id=payload.session_id,
        customer_name=policy.get("customer_name") if policy else claim.customer_name,
        phone=policy.get("phone") if policy else None,
        coverage=coverage_decision,
        dispatch=dispatch_plan,
    )
    session.notifications.append(customer_notification.message)

    observer_state = ObserverState(
        transcript=transcript,
        extracted_fields=claim.model_dump(exclude_none=True),
        coverage_decision=coverage_decision,
        dispatch_plan=dispatch_plan,
        audit_notes=[
            coverage_decision.reason,
            f"Decision source: {decision_source}.",
        ],
    )
    follow_up_questions = []
    if coverage_decision.manual_review_required:
        follow_up_questions.append("Confirm policy details with a human agent.")
    if conversation_service.missing_fields(claim):
        follow_up_questions.append("Some intake fields are incomplete.")

    return EvaluateClaimResponse(
        claim=claim,
        matched_policy=PolicyMatch(**policy) if policy else None,
        coverage_decision=coverage_decision,
        provider_candidates=provider_candidates,
        dispatch_plan=dispatch_plan,
        customer_notification=customer_notification,
        observer_state=observer_state,
        follow_up_questions=follow_up_questions,
        coverage_query=coverage_query,
        dispatch_query=dispatch_query,
        decision_source=decision_source,
    )


@router.post("/voice/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    session_id: str = Form("default"),
    audio: UploadFile = File(...),
) -> VoiceTurnResponse:
    audio_bytes = await audio.read()
    if not openai_service.available:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required for voice turns.")
    try:
        transcript_chunk = openai_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename or "voice-turn.webm",
            content_type=audio.content_type,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    session = session_store.get(session_id)
    session.transcript = f"{session.transcript} {transcript_chunk}".strip()
    claim, assistant_source = _extract_claim(session.transcript)
    missing_fields = conversation_service.missing_fields(claim)
    enough_information = not missing_fields
    try:
        assistant_text = _agent_reply(session.transcript, missing_fields, enough_information)
        assistant_audio_base64 = openai_service.synthesize_speech(assistant_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return VoiceTurnResponse(
        session_id=session_id,
        transcript=session.transcript,
        extracted_fields=claim.model_dump(exclude_none=True),
        missing_fields=missing_fields,
        next_prompt=conversation_service.next_prompt(claim),
        assistant_text=assistant_text,
        assistant_audio_base64=assistant_audio_base64,
        assistant_audio_mime_type="audio/mpeg" if assistant_audio_base64 else None,
        assistant_source=assistant_source,
    )


@router.get("/demo-scenarios")
def demo_scenarios() -> dict:
    return {
        "scenarios": data_service.scenarios(),
        "customers": data_service.customers(),
        "policies": data_service.policies(),
    }


@router.get("/notifications", response_model=NotificationFeedResponse)
def notifications_feed() -> NotificationFeedResponse:
    notifications = [NotificationRecord(**record) for record in database_service.notifications()]
    return NotificationFeedResponse(notifications=notifications)


@router.post("/reset")
def reset_session(session_id: str = "default") -> dict[str, str]:
    session_store.reset(session_id)
    return {"status": "ok", "session_id": session_id}


def _extract_claim(transcript: str) -> tuple[ClaimIntake, str]:
    if openai_service.available:
        try:
            return ClaimIntake(**openai_service.extract_claim(transcript)), "llm"
        except Exception:
            pass
    return claim_extraction_service.extract(transcript), "rules"


def _evaluate_coverage(claim: ClaimIntake, transcript: str) -> tuple:
    if openai_service.available:
        try:
            query_payload = openai_service.generate_policy_query(transcript, claim.model_dump())
            policies = database_service.execute_readonly(query_payload["sql_query"])
            if policies:
                coverage_decision, policy = coverage_service.evaluate(claim, matched_policy=policies[0])
                return coverage_decision, policy, query_payload["sql_query"], "llm"
        except Exception:
            pass
    coverage_decision, policy = coverage_service.evaluate(claim)
    return coverage_decision, policy, None, "rules"


def _recommend_dispatch(claim: ClaimIntake, coverage_decision, policy: dict) -> tuple:
    if openai_service.available and coverage_decision.status == "covered" and policy:
        try:
            query_payload = openai_service.generate_dispatch_query(claim.model_dump(), policy)
            provider_rows = database_service.execute_readonly(query_payload["provider_sql_query"])
            return dispatch_service.recommend(
                claim,
                coverage_decision,
                policy,
                provider_rows=provider_rows,
                forced_action=query_payload["action_type"],
            ) + (query_payload["provider_sql_query"],)
        except Exception:
            pass
    dispatch_plan, provider_candidates = dispatch_service.recommend(claim, coverage_decision, policy)
    return dispatch_plan, provider_candidates, None


def _agent_reply(transcript: str, missing_fields: list[str], enough_information: bool) -> str:
    if openai_service.available:
        try:
            return openai_service.generate_agent_reply(transcript, missing_fields, enough_information)
        except Exception:
            pass
    return conversation_service.next_prompt(_extract_claim(transcript)[0])
