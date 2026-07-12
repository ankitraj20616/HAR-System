"""Deterministic safety text used immediately and when inference fails."""

from __future__ import annotations

from typing import Any

from services.feedback_service.models import FeedbackContent

DISCLAIMER = "This is automated assistive information, not a medical diagnosis or medical advice."


def deterministic_feedback(mode: str, digest: dict[str, Any]) -> FeedbackContent:
    event = digest.get("event")
    if mode == "alert" and event:
        kind = str(event.get("type", "ABNORMAL_PATTERN")).replace("_", " ").lower()
        detected_at = str(event.get("detected_at", "the recorded time"))
        severity = str(event.get("severity", "warning"))
        headline = "Possible fall detected" if kind == "fall" else "Unusual activity detected"
        return FeedbackContent(
            headline=headline,
            detail=f"A {kind} event was detected at {detected_at}. Severity: {severity}.",
            severity="critical" if kind == "fall" else severity,
            recommendations=[
                "Check on the patient promptly and contact emergency services if "
                "immediate danger is present."
            ],
            disclaimer=DISCLAIMER,
        )

    samples = int(digest.get("sample_count", 0))
    durations = digest.get("activity_durations_seconds", {})
    if samples == 0:
        return FeedbackContent(
            headline="No activity data for this period",
            detail=(
                "No recorded activity samples were available, so no activity pattern was inferred."
            ),
            severity="info",
            recommendations=["Check that the monitoring services are online."],
            disclaimer=DISCLAIMER,
        )
    labels = ", ".join(
        f"{name.lower()}: {seconds:g} seconds" for name, seconds in durations.items()
    )
    return FeedbackContent(
        headline="Recorded activity summary" if mode == "summary" else "Recent activity feedback",
        detail=(
            f"The recorded period included {labels or 'activity samples with unknown duration'}."
        ),
        severity="warning" if digest.get("events") else "info",
        recommendations=[
            "Review the recorded timeline and contact a qualified professional with concerns."
        ],
        disclaimer=DISCLAIMER,
    )
