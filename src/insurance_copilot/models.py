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
    assistant_source: str = "rules"


class PolicyMatch(BaseModel):
    policy_reference: str
    customer_name: str
    customer_id: str | None = None
    phone: str | None = None
    status: str
    roadside_assistance: bool
    tow_covered: bool
    repair_van_covered: bool
    rental_or_taxi_covered: bool
    covered_regions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class CoverageDecision(BaseModel):
    status: CoverageStatus
    reason: str
    customer_explanation: str
    manual_review_required: bool = False
    confidence: float = 0.0


class ProviderCandidate(BaseModel):
    provider_name: str
    garage_name: str
    lat: float
    lon: float
    capabilities: list[str] = Field(default_factory=list)
    eta_minutes: int
    distance_score: float
    selected: bool = False


class DispatchPlan(BaseModel):
    action_type: ActionType
    provider_name: str
    garage_name: str
    eta_minutes: int
    ancillary_benefits: list[str] = Field(default_factory=list)
    provider_lat: float | None = None
    provider_lon: float | None = None


class CustomerNotification(BaseModel):
    channel: Literal["sms"] = "sms"
    message: str
    timestamp: datetime


class NotificationRecord(BaseModel):
    id: int
    session_id: str
    customer_name: str | None = None
    phone: str | None = None
    coverage_status: CoverageStatus | str
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
    matched_policy: PolicyMatch | None = None
    coverage_decision: CoverageDecision
    provider_candidates: list[ProviderCandidate] = Field(default_factory=list)
    dispatch_plan: DispatchPlan
    customer_notification: CustomerNotification
    observer_state: ObserverState
    follow_up_questions: list[str]
    coverage_query: str | None = None
    dispatch_query: str | None = None
    decision_source: str = "rules"


class NotificationFeedResponse(BaseModel):
    notifications: list[NotificationRecord] = Field(default_factory=list)


class VoiceTurnResponse(BaseModel):
    session_id: str
    transcript: str
    extracted_fields: dict[str, Any]
    missing_fields: list[str]
    next_prompt: str
    assistant_text: str
    assistant_audio_base64: str | None = None
    assistant_audio_mime_type: str | None = None
    assistant_source: str = "rules"
