"""Create compact, privacy-preserving timeline digests for the LLM."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any


def build_digest(
    from_ts: datetime,
    to_ts: datetime,
    activities: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    maximum_size: int,
    aggregates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Summarize facts without raw sensor arrays, landmarks, or frames."""

    ordered = sorted(activities, key=lambda row: row["ts"])
    durations: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    for index, row in enumerate(ordered):
        end = ordered[index + 1]["ts"] if index + 1 < len(ordered) else to_ts
        # Match the dashboard's bounded observed-interval policy. A sparse row
        # before an outage must never be described as minutes of activity.
        seconds = max(0.0, min((end - row["ts"]).total_seconds(), 5.0))
        durations[str(row["activity"])] += round(seconds, 1)
        if index:
            previous = str(ordered[index - 1]["activity"])
            current = str(row["activity"])
            if previous != current:
                transitions[f"{previous}->{current}"] += 1

    if aggregates is not None:
        durations = Counter(
            {str(row["activity"]): round(float(row["duration_seconds"]), 1) for row in aggregates}
        )
        sample_count = sum(int(row["count"]) for row in aggregates)
    else:
        sample_count = len(ordered)

    digest: dict[str, Any] = {
        "time_range": {"from": from_ts.isoformat(), "to": to_ts.isoformat()},
        "sample_count": sample_count,
        "activity_durations_seconds": dict(sorted(durations.items())),
        "transitions": dict(sorted(transitions.items())),
        "events": [
            {
                "type": str(row["type"]),
                "detected_at": row["ts"].isoformat(),
                "severity": str(row["severity"]),
                "confidence": round(float(row["confidence"]), 3),
            }
            for row in sorted(events, key=lambda row: row["ts"])
        ],
        "unknown_data_caveat": "The digest includes only recorded samples in this period.",
    }

    def encoded_size() -> int:
        return len(json.dumps(digest, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    if encoded_size() <= maximum_size:
        return digest
    # Retain the newest/safest facts and explicitly disclose truncation.
    digest["digest_truncated"] = True
    while digest["events"] and encoded_size() > maximum_size:
        digest["events"].pop(0)
    while digest["transitions"] and encoded_size() > maximum_size:
        digest["transitions"].pop(next(iter(digest["transitions"])))
    while digest["activity_durations_seconds"] and encoded_size() > maximum_size:
        digest["activity_durations_seconds"].pop(next(iter(digest["activity_durations_seconds"])))
    return digest


def event_digest(event: Any) -> dict[str, Any]:
    return {
        "event": {
            "type": str(event.type),
            "detected_at": event.ts.isoformat(),
            "severity": str(event.severity),
            "confidence": round(float(event.confidence), 3),
            "evidence_summary": sorted(str(key) for key in event.evidence),
        }
    }
