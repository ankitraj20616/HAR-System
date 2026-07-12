"""Post-generation medical-safety and supplied-facts-only checks."""

from __future__ import annotations

import json
import re
from typing import Any

from services.feedback_service.models import FeedbackContent

DISCLAIMER_TERMS = ("not a medical diagnosis", "not medical advice")
FORBIDDEN_PATTERNS = (
    r"\b(?:you|the patient|patient) (?:have|has|had|suffer(?:s|ed)? from|is|was) "
    r"(?:diagnosed|unconscious|injured|bleeding)\b",
    r"\bdiagnos(?:e|ed|is|ing) (?:you|the patient|them)\b",
    r"\b(?:blood pressure|heart rate|pulse|oxygen saturation|spo2|temperature|blood sugar)\b",
    r"\b(?:fracture|concussion|stroke|seizure|heart attack|parkinson'?s?|dementia|"
    r"infection|injury|bleeding|unconscious|loss of consciousness)\b",
    r"\b(?:indicates?|suggests?|symptoms? of|signs? of|likely|probably|may have|could have)\b"
    r".{0,60}\b(?:disease|disorder|condition|syndrome)\b",
    r"\b(?:caused by|because of|due to)\b",
    r"\b(?:patient'?s? name|named patient|patient is (?:male|female|a man|a woman|\d+ years))\b",
)


class SafetyViolation(ValueError):
    pass


def validate_safety(content: FeedbackContent, digest: dict[str, Any]) -> None:
    combined = " ".join(
        [content.headline, content.detail, *content.recommendations, content.disclaimer]
    ).casefold()
    if not any(term in content.disclaimer.casefold() for term in DISCLAIMER_TERMS):
        raise SafetyViolation("a clear medical disclaimer is required")
    if any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS):
        raise SafetyViolation("diagnostic or unsupported medical claim detected")

    supplied = json.dumps(digest, default=str).casefold()
    # Explicit event/activity names in prose must occur in the digest. This is
    # deliberately narrow to avoid treating ordinary language as a false claim.
    factual_tokens = (
        "walking",
        "sitting",
        "standing",
        "lying",
        "exercising",
        "fall",
        "inactivity",
        "abnormal pattern",
    )
    unsupported = [token for token in factual_tokens if token in combined and token not in supplied]
    if unsupported:
        raise SafetyViolation(f"unsupported supplied-fact claim: {unsupported[0]}")
