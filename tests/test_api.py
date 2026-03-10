from fastapi.testclient import TestClient

from insurance_copilot.app import app
from insurance_copilot.dependencies import database_service, openai_service


client = TestClient(app)


def setup_function() -> None:
    database_service.reset_notifications()


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Insurance Co-Pilot" in response.text


def test_notifications_page_renders() -> None:
    response = client.get("/notifications")
    assert response.status_code == 200
    assert "Customer Update Feed" in response.text


def test_demo_scenarios_route() -> None:
    response = client.get("/api/demo-scenarios")
    assert response.status_code == 200
    body = response.json()
    assert len(body["scenarios"]) == 3


def test_transcript_then_evaluate_flow() -> None:
    transcript = (
        "This is Alice Johnson policy POL-1001 in city at 40.73,-73.98. "
        "Flat battery and drivable. 2 passengers and low safety risk."
    )
    t_response = client.post("/api/transcript", json={"session_id": "test", "chunk": transcript})
    assert t_response.status_code == 200
    assert "policy_reference" in t_response.json()["extracted_fields"]

    e_response = client.post("/api/claims/evaluate", json={"session_id": "test"})
    assert e_response.status_code == 200
    body = e_response.json()
    assert body["coverage_decision"]["status"] == "covered"
    assert body["matched_policy"]["policy_reference"] == "POL-1001"
    assert body["dispatch_plan"]["action_type"] in {"repair_van", "tow_truck"}
    assert len(body["provider_candidates"]) >= 1


def test_not_covered_policy() -> None:
    transcript = (
        "I am Carlos Diaz policy POL-1003 off road at 40.71,-74.01. "
        "Vehicle not drivable and medium safety risk."
    )
    client.post("/api/transcript", json={"session_id": "not-covered", "chunk": transcript})
    e_response = client.post("/api/claims/evaluate", json={"session_id": "not-covered"})
    assert e_response.status_code == 200
    assert e_response.json()["coverage_decision"]["status"] == "not_covered"


def test_notifications_feed_includes_sent_update() -> None:
    client.post(
        "/api/transcript",
        json={
            "session_id": "notify-test",
            "chunk": (
                "This is Alice Johnson policy POL-1001 in city at 40.73,-73.98. "
                "Flat battery and drivable. 2 passengers and low safety risk."
            ),
        },
    )
    client.post("/api/claims/evaluate", json={"session_id": "notify-test"})

    response = client.get("/api/notifications")
    assert response.status_code == 200
    body = response.json()
    assert len(body["notifications"]) == 1
    assert body["notifications"][0]["customer_name"] == "Alice Johnson"


def test_transcript_route_extracts_from_full_accumulated_conversation(monkeypatch) -> None:
    seen_transcripts: list[str] = []
    original_key = openai_service._api_key
    openai_service._api_key = "test-key"

    def fake_extract(transcript: str) -> dict:
        seen_transcripts.append(transcript)
        return {
            "customer_name": "Brian Smith",
            "policy_reference": "POL-1002",
            "vehicle": None,
            "location": "highway",
            "issue_type": "engine_failure",
            "is_drivable": False,
            "safety_risk": None,
            "passenger_count": None,
        }

    monkeypatch.setattr(openai_service, "extract_claim", fake_extract)
    try:
        client.post("/api/transcript", json={"session_id": "multi-turn", "chunk": "Hi, I'm Brian Smith."})
        client.post(
            "/api/transcript",
            json={"session_id": "multi-turn", "chunk": "My policy ID is POL1002 and the vehicle is not drivable."},
        )
    finally:
        openai_service._api_key = original_key

    assert len(seen_transcripts) == 2
    assert seen_transcripts[1] == "Hi, I'm Brian Smith. My policy ID is POL1002 and the vehicle is not drivable."
