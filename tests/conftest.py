from __future__ import annotations

import os

import pytest

from insurance_copilot.config import load_dotenv


load_dotenv(override=True)

try:
    from insurance_copilot.dependencies import claim_extraction_service, conversation_service, openai_service
except Exception:
    openai_service = None


@pytest.fixture(autouse=True)
def isolate_live_openai_from_default_tests(request, monkeypatch):
    if openai_service is None:
        yield
        return

    original_key = openai_service._api_key
    if "openai_integration" not in request.keywords:
        openai_service._api_key = "test-openai-key"

        def fake_extract_claim(transcript: str) -> dict:
            return claim_extraction_service.extract(transcript).model_dump()

        def fake_generate_policy_query(transcript: str, claim: dict) -> dict:
            if claim.get("policy_reference"):
                sql_query = (
                    "SELECT * FROM policy_directory "
                    f"WHERE policy_reference = '{claim['policy_reference']}' LIMIT 1"
                )
            elif claim.get("customer_name"):
                sql_query = (
                    "SELECT * FROM policy_directory "
                    f"WHERE lower(customer_name) = lower('{claim['customer_name']}') LIMIT 1"
                )
            else:
                sql_query = "SELECT * FROM policy_directory LIMIT 1"
            return {"sql_query": sql_query, "lookup_reason": "test stub"}

        def fake_generate_dispatch_query(claim: dict, policy: dict) -> dict:
            action_type = (
                "tow_truck"
                if claim.get("is_drivable") is False or claim.get("issue_type") in {"engine_failure", "collision"}
                else "repair_van"
            )
            return {
                "action_type": action_type,
                "provider_sql_query": (
                    "SELECT provider_name, garage_name, lat, lon, capabilities "
                    f"FROM providers WHERE instr(capabilities, '{action_type}') > 0 LIMIT 4"
                ),
                "reason": "test stub",
            }

        def fake_generate_agent_reply(transcript: str, missing_fields: list[str], enough_information: bool) -> str:
            claim = claim_extraction_service.extract(transcript)
            if enough_information:
                return "I have enough information to assess coverage and dispatch help."
            return conversation_service.next_prompt(claim)

        monkeypatch.setattr(openai_service, "extract_claim", fake_extract_claim)
        monkeypatch.setattr(openai_service, "generate_policy_query", fake_generate_policy_query)
        monkeypatch.setattr(openai_service, "generate_dispatch_query", fake_generate_dispatch_query)
        monkeypatch.setattr(openai_service, "generate_agent_reply", fake_generate_agent_reply)
    try:
        yield
    finally:
        openai_service._api_key = original_key
