from insurance_copilot.models import ClaimIntake, CoverageDecision
from insurance_copilot.services.claim_extraction_service import ClaimExtractionService
from insurance_copilot.services.database_service import DatabaseService
from insurance_copilot.services.coverage_service import CoverageService
from insurance_copilot.services.dispatch_service import DispatchService
from insurance_copilot.services.notification_service import NotificationService


def test_coverage_for_active_policy_is_covered() -> None:
    coverage_service = CoverageService(DatabaseService())
    claim = ClaimIntake(
        customer_name="Alice Johnson",
        policy_reference="POL-1001",
        location="city:40.73,-73.98",
        issue_type="flat_battery",
        is_drivable=True,
    )
    decision, _ = coverage_service.evaluate(claim)
    assert decision.status == "covered"


def test_lapsed_policy_is_not_covered() -> None:
    coverage_service = CoverageService(DatabaseService())
    claim = ClaimIntake(
        customer_name="Carlos Diaz",
        policy_reference="POL-1003",
        location="city:40.73,-73.98",
        issue_type="engine_failure",
        is_drivable=False,
    )
    decision, _ = coverage_service.evaluate(claim)
    assert decision.status == "not_covered"


def test_dispatch_selects_tow_for_non_drivable() -> None:
    dispatch_service = DispatchService(DatabaseService())
    plan, candidates = dispatch_service.recommend(
        ClaimIntake(location="city:40.75,-73.96", issue_type="engine_failure", is_drivable=False),
        CoverageDecision(
            status="covered",
            reason="ok",
            customer_explanation="ok",
            confidence=0.9,
        ),
        {"tow_covered": True, "repair_van_covered": True, "rental_or_taxi_covered": False},
    )
    assert plan.action_type == "tow_truck"
    assert candidates[0].selected is True


def test_dispatch_selects_repair_for_drivable_battery() -> None:
    dispatch_service = DispatchService(DatabaseService())
    plan, _ = dispatch_service.recommend(
        ClaimIntake(location="city:40.73,-73.98", issue_type="flat_battery", is_drivable=True),
        CoverageDecision(
            status="covered",
            reason="ok",
            customer_explanation="ok",
            confidence=0.9,
        ),
        {"tow_covered": True, "repair_van_covered": True, "rental_or_taxi_covered": True},
    )
    assert plan.action_type == "repair_van"


def test_notification_contains_eta_when_covered() -> None:
    database_service = DatabaseService()
    database_service.reset_notifications()
    notification_service = NotificationService(database_service)
    dispatch_plan, _ = DispatchService(database_service).recommend(
        ClaimIntake(location="city:40.73,-73.98", issue_type="flat_battery", is_drivable=True),
        CoverageDecision(
            status="covered",
            reason="ok",
            customer_explanation="ok",
            confidence=0.9,
        ),
        {"tow_covered": True, "repair_van_covered": True, "rental_or_taxi_covered": True},
    )
    notification = notification_service.build_message(
        CoverageDecision(
            status="covered",
            reason="ok",
            customer_explanation="ok",
            confidence=0.9,
        ),
        dispatch=dispatch_plan,
    )
    assert "ETA" in notification.message
    assert dispatch_plan.eta_minutes > 0


def test_normalize_claim_prefers_policy_digits_from_transcript() -> None:
    service = ClaimExtractionService()
    claim = ClaimIntake(policy_reference="POL-1234")
    normalized = service.normalize_claim(
        claim,
        "Hi, I'm Brian Smith and my policy number is 1002.",
    )
    assert normalized.policy_reference == "POL-1002"
