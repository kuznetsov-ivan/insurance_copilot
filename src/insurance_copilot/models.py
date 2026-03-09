from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


CoverageStatus = Literal["covered", "not_covered", "manual_review"]
ActionType = Literal["tow_truck", "repair_van", "manual_escalation", "none"]


class ClaimIntake(BaseModel):
    customer_name: str | None = None
    policy_reference: str | None = None
    vehicle: str | None = None
    location: str | None = None
    issue_type: str | None = None
    is_drivable: bool | None = None
    safety_risk: str | None = None
    passenger_count: int | None = None


class TranscriptRequest(BaseModel):
    session_id: str = "default"
    chunk: str = Field(min_length=1)


class TranscriptResponse(BaseModel):
    session_id: str
    transcript: str
    extracted_fields: dict[str, Any]
    missing_fields: list[str]
    next_prompt: str


class CoverageDecision(BaseModel):
    status: CoverageStatus
    reason: str
    customer_explanation: str
    manual_review_required: bool = False
    confidence: float = 0.0


class DispatchPlan(BaseModel):
    action_type: ActionType
    provider_name: str
    garage_name: str
    eta_minutes: int
    ancillary_benefits: list[str] = Field(default_factory=list)


class CustomerNotification(BaseModel):
    channel: Literal["sms"] = "sms"
    message: str
    timestamp: datetime


class ObserverState(BaseModel):
    transcript: str
    extracted_fields: dict[str, Any]
    coverage_decision: CoverageDecision
    dispatch_plan: DispatchPlan
    audit_notes: list[str] = Field(default_factory=list)


class EvaluateClaimRequest(BaseModel):
    session_id: str = "default"
    transcript: str | None = None
    claim: ClaimIntake | None = None


class EvaluateClaimResponse(BaseModel):
    claim: ClaimIntake
    coverage_decision: CoverageDecision
    dispatch_plan: DispatchPlan
    customer_notification: CustomerNotification
    observer_state: ObserverState
    follow_up_questions: list[str]

