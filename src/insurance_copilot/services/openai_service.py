from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any


class OpenAIService:
    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._base_url = "https://api.openai.com/v1"

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def transcribe_audio(self, *, audio_bytes: bytes, filename: str, content_type: str | None) -> str:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        boundary = f"----OpenAIBoundary{uuid.uuid4().hex}"
        multipart = []
        multipart.extend(self._form_part(boundary, "model", b"gpt-4o-mini-transcribe"))
        multipart.extend(
            self._file_part(
                boundary,
                "file",
                filename,
                content_type or "audio/webm",
                audio_bytes,
            )
        )
        multipart.append(f"--{boundary}--\r\n".encode("utf-8"))
        response = self._request(
            path="/audio/transcriptions",
            body=b"".join(multipart),
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        return response["text"].strip()

    def synthesize_speech(self, text: str) -> str | None:
        if not self.available:
            return None

        audio_bytes = self._request_bytes(
            path="/audio/speech",
            body=json.dumps(
                {
                    "model": "gpt-4o-mini-tts",
                    "voice": "coral",
                    "input": text,
                    "instructions": "Speak like a calm insurance assistant. Keep the tone clear and warm.",
                    "response_format": "mp3",
                }
            ).encode("utf-8"),
            content_type="application/json",
        )
        return base64.b64encode(audio_bytes).decode("utf-8")

    def extract_claim(self, transcript: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "customer_name": {"type": ["string", "null"]},
                "policy_reference": {"type": ["string", "null"]},
                "vehicle": {"type": ["string", "null"]},
                "location": {"type": ["string", "null"]},
                "issue_type": {"type": ["string", "null"]},
                "is_drivable": {"type": ["boolean", "null"]},
                "safety_risk": {"type": ["string", "null"]},
                "passenger_count": {"type": ["integer", "null"]},
            },
            "required": [
                "customer_name",
                "policy_reference",
                "vehicle",
                "location",
                "issue_type",
                "is_drivable",
                "safety_risk",
                "passenger_count",
            ],
            "additionalProperties": False,
        }
        system = (
            "Extract structured roadside assistance claim intake data. "
            "Normalize location to region:lat,lon when coordinates are present. "
            "Allowed issue_type values: flat_battery, engine_failure, flat_tire, collision. "
            "Allowed safety_risk values: low, medium, high."
        )
        return self._structured_json("claim_extraction", system, transcript, schema)

    def generate_policy_query(self, transcript: str, claim: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string"},
                "lookup_reason": {"type": "string"},
            },
            "required": ["sql_query", "lookup_reason"],
            "additionalProperties": False,
        }
        system = (
            "Convert the claim transcript into a single read-only SQLite SELECT query against the "
            "policy_directory table. The table columns are policy_reference, customer_name, customer_id, phone, "
            "status, roadside_assistance, tow_covered, repair_van_covered, rental_or_taxi_covered, "
            "covered_regions, exclusions. Only generate one SELECT statement with LIMIT 1."
        )
        user = json.dumps({"transcript": transcript, "claim": claim})
        return self._structured_json("policy_lookup", system, user, schema)

    def generate_dispatch_query(self, claim: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "action_type": {"type": "string"},
                "provider_sql_query": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["action_type", "provider_sql_query", "reason"],
            "additionalProperties": False,
        }
        system = (
            "Choose the best roadside response action and produce a read-only SQLite SELECT query against the "
            "providers table. Providers columns are provider_name, garage_name, lat, lon, capabilities. "
            "Allowed action_type values: tow_truck, repair_van, manual_escalation. "
            "If manual_escalation, return SELECT provider_name, garage_name, lat, lon, capabilities FROM providers LIMIT 4."
        )
        user = json.dumps({"claim": claim, "policy": policy})
        return self._structured_json("dispatch_lookup", system, user, schema)

    def generate_agent_reply(self, transcript: str, missing_fields: list[str], enough_information: bool) -> str:
        schema = {
            "type": "object",
            "properties": {"reply": {"type": "string"}},
            "required": ["reply"],
            "additionalProperties": False,
        }
        system = (
            "You are a voice intake insurance agent. Reply in one or two short sentences. "
            "If enough_information is false, ask only for the most important missing field next. "
            "If enough_information is true, confirm you have enough to assess coverage and dispatch help."
        )
        user = json.dumps(
            {
                "transcript": transcript,
                "missing_fields": missing_fields,
                "enough_information": enough_information,
            }
        )
        response = self._structured_json("voice_reply", system, user, schema)
        return response["reply"]

    def _structured_json(
        self,
        schema_name: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        response = self._request(
            path="/chat/completions",
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)

    def _request(self, *, path: str, body: bytes, content_type: str) -> dict[str, Any]:
        raw = self._request_bytes(path=path, body=body, content_type=content_type)
        return json.loads(raw.decode("utf-8"))

    def _request_bytes(self, *, path: str, body: bytes, content_type: str) -> bytes:
        request = urllib.request.Request(
            url=f"{self._base_url}{path}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": content_type,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc

    def _form_part(self, boundary: str, name: str, value: bytes) -> list[bytes]:
        return [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
            value,
            b"\r\n",
        ]

    def _file_part(
        self,
        boundary: str,
        name: str,
        filename: str,
        content_type: str,
        value: bytes,
    ) -> list[bytes]:
        return [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8"),
            value,
            b"\r\n",
        ]
