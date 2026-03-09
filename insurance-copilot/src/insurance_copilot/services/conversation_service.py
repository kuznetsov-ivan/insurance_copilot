from __future__ import annotations

from insurance_copilot.models import ClaimIntake


class ConversationService:
    QUESTIONS = [
        "Please share your full name.",
        "What is your policy ID or registered phone number?",
        "What car are you driving (make and model)?",
        "Where is your current location?",
        "What happened to the vehicle?",
        "Is the car drivable right now?",
        "How many passengers are with you?",
        "What is your safety situation right now?",
    ]

    FIELD_PROMPTS = {
        "customer_name": QUESTIONS[0],
        "policy_reference": QUESTIONS[1],
        "vehicle": QUESTIONS[2],
        "location": QUESTIONS[3],
        "issue_type": QUESTIONS[4],
        "is_drivable": QUESTIONS[5],
        "passenger_count": QUESTIONS[6],
        "safety_risk": QUESTIONS[7],
    }

    def missing_fields(self, claim: ClaimIntake) -> list[str]:
        missing = []
        for field in self.FIELD_PROMPTS:
            if getattr(claim, field) in (None, ""):
                missing.append(field)
        return missing

    def next_prompt(self, claim: ClaimIntake) -> str:
        missing = self.missing_fields(claim)
        if not missing:
            return "Thanks. I have enough information and can start assessment."
        return self.FIELD_PROMPTS[missing[0]]

