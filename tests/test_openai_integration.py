from __future__ import annotations

import base64
import os

import pytest

from insurance_copilot.services.openai_service import OpenAIService


RUN_OPENAI_INTEGRATION = os.getenv("RUN_OPENAI_INTEGRATION") == "1"
HAS_OPENAI_KEY = bool(os.getenv("OPENAI_API_KEY"))


pytestmark = [
    pytest.mark.openai_integration,
    pytest.mark.skipif(
        not RUN_OPENAI_INTEGRATION,
        reason="Set RUN_OPENAI_INTEGRATION=1 to run live OpenAI integration tests.",
    ),
    pytest.mark.skipif(
        not HAS_OPENAI_KEY,
        reason="OPENAI_API_KEY is required for live OpenAI integration tests.",
    ),
]


@pytest.fixture
def openai_service() -> OpenAIService:
    service = OpenAIService()
    assert service.available, "OPENAI_API_KEY must be configured for integration tests."
    print(f"OPENAI_API_KEY suffix: {os.environ['OPENAI_API_KEY'][-5:]}")
    return service


def _skip_on_live_openai_unavailable(error: RuntimeError) -> None:
    message = str(error)
    transient_markers = (
        "nodename nor servname provided",
        "Name or service not known",
        "Temporary failure in name resolution",
        "not_authorized_invalid_key_type",
        "OPENAI request failed (401)",
    )
    if any(marker in message for marker in transient_markers):
        pytest.skip(f"Live OpenAI API unavailable for integration run: {message}")
    raise error


def test_chat_model_extracts_and_generates_queries(openai_service: OpenAIService) -> None:
    transcript = (
        "This is Alice Johnson, policy POL-1001. I am in the city at 40.73,-73.98. "
        "My car has a flat battery but it is still drivable. There are 2 passengers and low safety risk."
    )

    try:
        claim = openai_service.extract_claim(transcript)
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    assert claim["customer_name"] == "Alice Johnson"
    assert claim["policy_reference"] == "POL-1001"
    assert claim["issue_type"] == "flat_battery"
    assert claim["is_drivable"] is True

    try:
        policy_query = openai_service.generate_policy_query(transcript, claim)
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    assert "select" in policy_query["sql_query"].lower()
    assert "policy_directory" in policy_query["sql_query"].lower()

    try:
        dispatch_query = openai_service.generate_dispatch_query(
            claim,
            {
                "policy_reference": "POL-1001",
                "customer_name": "Alice Johnson",
                "status": "active",
                "roadside_assistance": True,
                "tow_covered": True,
                "repair_van_covered": True,
                "rental_or_taxi_covered": True,
                "covered_regions": ["city", "highway"],
                "exclusions": ["off_road"],
            },
        )
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    assert dispatch_query["action_type"] in {"tow_truck", "repair_van", "manual_escalation"}
    assert "select" in dispatch_query["provider_sql_query"].lower()
    assert "providers" in dispatch_query["provider_sql_query"].lower()

    try:
        agent_reply = openai_service.generate_agent_reply(transcript, [], enough_information=True)
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    assert isinstance(agent_reply, str)
    assert len(agent_reply.strip()) > 0


def test_tts_and_transcription_models_round_trip(openai_service: OpenAIService) -> None:
    source_text = "This is Alice Johnson with a flat battery in the city."

    try:
        audio_base64 = openai_service.synthesize_speech(source_text)
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    assert audio_base64

    audio_bytes = base64.b64decode(audio_base64)
    assert len(audio_bytes) > 100

    try:
        transcript = openai_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename="roundtrip.mp3",
            content_type="audio/mpeg",
        )
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    normalized = transcript.lower()
    assert "alice" in normalized
    assert "battery" in normalized


def test_chat_model_extracts_from_accumulated_conversation(openai_service: OpenAIService) -> None:
    transcript = " ".join(
        [
            "Hi, I'm Brian Smith. The engine does not start and I am stuck on the M1 road.",
            "My policy ID is POL1002. It is one zero zero two. The vehicle is not drivable.",
        ]
    )

    try:
        claim = openai_service.extract_claim(transcript)
    except RuntimeError as error:
        _skip_on_live_openai_unavailable(error)
    assert claim["customer_name"] == "Brian Smith"
    assert claim["policy_reference"] in {"POL1002", "POL-1002"}
    assert claim["issue_type"] == "engine_failure"
    assert claim["is_drivable"] is False
