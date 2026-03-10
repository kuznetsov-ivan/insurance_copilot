from __future__ import annotations

import re

from insurance_copilot.models import ClaimIntake


class ClaimExtractionService:
    _policy_pattern = re.compile(r"\bPOL[-\s]?\d{4}\b", flags=re.IGNORECASE)
    _name_pattern = re.compile(r"(?:this is|i am|i'm)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", flags=re.IGNORECASE)
    _passengers_pattern = re.compile(r"(\d+)\s+passenger", flags=re.IGNORECASE)
    _location_pattern = re.compile(r"(-?\d{1,2}\.\d+,\s*-?\d{1,3}\.\d+)")
    _digit_words = {
        "zero": "0",
        "oh": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
    }

    def extract(self, transcript: str) -> ClaimIntake:
        text = transcript.strip()
        lower = text.lower()
        claim = ClaimIntake()

        claim.policy_reference = self._extract_policy_reference(text)

        name_match = self._name_pattern.search(text)
        if name_match:
            claim.customer_name = name_match.group(1).strip().title()

        if "not drivable" in lower or "cannot drive" in lower:
            claim.is_drivable = False
        elif "drivable" in lower:
            claim.is_drivable = True

        if "engine" in lower:
            claim.issue_type = "engine_failure"
        elif "battery" in lower:
            claim.issue_type = "flat_battery"
        elif "flat tire" in lower or "puncture" in lower:
            claim.issue_type = "flat_tire"
        elif "accident" in lower:
            claim.issue_type = "collision"

        if "highway" in lower:
            claim.location = "highway"
        elif "off road" in lower or "trail" in lower:
            claim.location = "off_road"
        elif "city" in lower or "downtown" in lower:
            claim.location = "city"

        lat_lon = self._location_pattern.search(text)
        if lat_lon:
            location = claim.location or ""
            claim.location = f"{location}:{lat_lon.group(1)}" if location else lat_lon.group(1)

        passengers_match = self._passengers_pattern.search(text)
        if passengers_match:
            claim.passenger_count = int(passengers_match.group(1))

        if "high safety risk" in lower:
            claim.safety_risk = "high"
        elif "medium safety risk" in lower:
            claim.safety_risk = "medium"
        elif "low safety risk" in lower or "no safety risk" in lower:
            claim.safety_risk = "low"

        vehicle = self._extract_vehicle(lower)
        if vehicle:
            claim.vehicle = vehicle

        return self.normalize_claim(claim, text)

    def normalize_claim(self, claim: ClaimIntake, transcript: str) -> ClaimIntake:
        transcript_policy_reference = self._extract_policy_reference(transcript)
        if transcript_policy_reference:
            claim.policy_reference = transcript_policy_reference
        elif claim.policy_reference:
            policy_digits = re.sub(r"[^0-9]", "", claim.policy_reference)
            if len(policy_digits) == 4:
                claim.policy_reference = f"POL-{policy_digits}"
        return claim

    def _extract_policy_reference(self, transcript: str) -> str | None:
        direct_match = self._policy_pattern.search(transcript)
        if direct_match:
            policy_digits = re.sub(r"[^0-9]", "", direct_match.group(0))
            if len(policy_digits) == 4:
                return f"POL-{policy_digits}"

        digitized = re.sub(
            r"\b(" + "|".join(self._digit_words.keys()) + r")\b",
            lambda match: self._digit_words[match.group(1).lower()],
            transcript,
            flags=re.IGNORECASE,
        )
        pattern = re.compile(
            r"\b(?:policy(?:\s+(?:id|number))?(?:\s+is)?\s+)?POL[-\s]?(\d{4})\b|\bpolicy(?:\s+(?:id|number))?(?:\s+is)?\s+(\d{4})\b",
            flags=re.IGNORECASE,
        )
        digitized_match = pattern.search(digitized)
        if digitized_match:
            policy_digits = digitized_match.group(1) or digitized_match.group(2)
            return f"POL-{policy_digits}"
        return None

    def _extract_vehicle(self, lower_transcript: str) -> str | None:
        markers = ("car", "vehicle", "driving")
        for marker in markers:
            idx = lower_transcript.find(marker)
            if idx == -1:
                continue
            snippet = lower_transcript[max(0, idx - 20): idx + 35]
            cleaned = re.sub(r"[^a-z0-9\s-]", "", snippet)
            return cleaned.strip()[:40]
        return None
