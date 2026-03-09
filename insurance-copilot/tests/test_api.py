from fastapi.testclient import TestClient

from insurance_copilot.app import app


client = TestClient(app)


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Insurance Co-Pilot" in response.text


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
    assert body["dispatch_plan"]["action_type"] in {"repair_van", "tow_truck"}


def test_not_covered_policy() -> None:
    transcript = (
        "I am Carlos Diaz policy POL-1003 off road at 40.71,-74.01. "
        "Vehicle not drivable and medium safety risk."
    )
    client.post("/api/transcript", json={"session_id": "not-covered", "chunk": transcript})
    e_response = client.post("/api/claims/evaluate", json={"session_id": "not-covered"})
    assert e_response.status_code == 200
    assert e_response.json()["coverage_decision"]["status"] == "not_covered"
