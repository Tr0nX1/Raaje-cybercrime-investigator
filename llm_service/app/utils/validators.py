from __future__ import annotations

import json
import re
from typing import Any

from app.models.request_models import TransactionInput

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def parse_json_object_from_text(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise ValueError("Model response is not text")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    match = JSON_OBJECT_PATTERN.search(cleaned)
    if not match:
        raise ValueError("No JSON object found in model response")

    return json.loads(match.group(0))


def normalize_model_payload(payload: dict[str, Any], original: TransactionInput) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Parsed payload must be an object")

    normalized = {
        "source_account": _string_or_empty(payload.get("source_account", original.source_account)),
        "source_utr": _string_or_empty(payload.get("source_utr", "")),
        "destination_account": _string_or_empty(
            payload.get("destination_account", original.destination_account)
        ),
        "destination_ifsc": _string_or_empty(payload.get("destination_ifsc", "")),
        "bank": _string_or_empty(payload.get("bank", original.bank)),
        "amount": _string_or_empty(payload.get("amount", original.amount)),
        "confidence": _normalize_confidence(payload.get("confidence")),
    }

    if not normalized["source_account"]:
        raise ValueError("source_account cannot be empty")
    if not normalized["destination_account"]:
        raise ValueError("destination_account cannot be empty")
    if not normalized["bank"]:
        raise ValueError("bank cannot be empty")
    if not normalized["amount"]:
        raise ValueError("amount cannot be empty")

    if normalized["destination_ifsc"] and not IFSC_PATTERN.fullmatch(normalized["destination_ifsc"]):
        raise ValueError("destination_ifsc is invalid")

    return normalized


def build_fallback_response(original: TransactionInput) -> dict[str, str]:
    return {
        "source_account": original.source_account.strip(),
        "source_utr": "",
        "destination_account": original.destination_account.strip(),
        "destination_ifsc": "",
        "bank": original.bank.strip(),
        "amount": original.amount.strip(),
        "confidence": "low",
    }


def _string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


def _normalize_confidence(value: Any) -> str:
    confidence = _string_or_empty(value).lower()
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError("confidence must be one of high, medium, low")
    return confidence
