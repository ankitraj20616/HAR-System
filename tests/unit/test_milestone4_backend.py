from datetime import UTC, datetime, timedelta

import pytest

from services.fusion_service.api import _timeline_records
from services.fusion_service.config import FusionSettings
from services.fusion_service.runtime import FusionMQTTDependency
from shared.db import (
    get_feedback_between,
    get_feedback_by_idempotency_key,
    get_latest_feedback,
    insert_feedback,
)
from shared.schemas import Feedback, FusedActivity


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = connection.description

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.connection.executions.append((query, params))

    def fetchone(self):
        return self.connection.fetchone

    def fetchall(self):
        return self.connection.fetchall


class Connection:
    def __init__(self, *, fetchone=None, fetchall=None, columns=()):
        self.fetchone = fetchone
        self.fetchall = fetchall or []
        self.description = [(column,) for column in columns]
        self.executions = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_feedback_idempotency_key_is_validated_and_used_for_conflict_retry() -> None:
    feedback = Feedback(
        ts="2026-07-11T10:00:00Z",
        mode="summary",
        headline="Daily activity summary",
        detail="Walking was recorded during the selected period.",
        severity="info",
        recommendations=["Continue following the usual care plan."],
        disclaimer="This automated summary is not a medical diagnosis.",
    )
    connection = Connection(fetchone=(12,))

    assert insert_feedback(connection, feedback, " request:daily:2026-07-11 ") == 12
    query, params = connection.executions[0]
    assert "ON CONFLICT (idempotency_key)" in query
    assert params[-2] == "request:daily:2026-07-11"

    with pytest.raises(ValueError):
        insert_feedback(Connection(fetchone=(1,)), feedback, " ")
    with pytest.raises(TypeError):
        insert_feedback(Connection(fetchone=(1,)), feedback, 7)  # type: ignore[arg-type]


def test_feedback_readers_support_latest_mode_key_and_utc_range() -> None:
    columns = (
        "id",
        "ts",
        "mode",
        "headline",
        "detail",
        "severity",
        "payload",
        "idempotency_key",
    )
    ts = datetime(2026, 7, 11, 10, tzinfo=UTC)
    row = (1, ts, "alert", "Fall", "Possible fall", "critical", {}, "event:1")

    latest = Connection(fetchone=row, columns=columns)
    assert get_latest_feedback(latest, "alert")["id"] == 1
    assert latest.executions[0][1] == ("alert", "alert")

    by_key = Connection(fetchone=row, columns=columns)
    assert get_feedback_by_idempotency_key(by_key, " event:1 ")["id"] == 1
    assert by_key.executions[0][1] == ("event:1",)

    ranged = Connection(fetchall=[row], columns=columns)
    assert get_feedback_between(ranged, ts, ts + timedelta(hours=1))[0]["id"] == 1
    assert ranged.executions[0][1] == (ts, ts + timedelta(hours=1), 1000)

    with pytest.raises(ValueError):
        get_latest_feedback(Connection(), "diagnosis")


def test_timeline_durations_are_bounded_across_stream_gaps() -> None:
    start = datetime(2026, 7, 11, 10, tzinfo=UTC)
    base = {
        "confidence": 0.9,
        "sensor_label": "WALKING",
        "video_label": "WALKING",
    }
    rows = [
        {"id": 1, "ts": start, "activity": "WALKING", **base},
        {"id": 2, "ts": start + timedelta(seconds=20), "activity": "SITTING", **base},
    ]

    records = _timeline_records(rows, start + timedelta(seconds=21), 2.0)

    assert [record.duration_seconds for record in records] == [2.0, 1.0]


def test_status_distinguishes_current_stale_and_unavailable_activity() -> None:
    settings = FusionSettings(stale_timeout_seconds=3.0)
    runtime = FusionMQTTDependency(settings)
    now = datetime(2026, 7, 11, 10, tzinfo=UTC)

    assert runtime.status(now).data_status == "unavailable"
    runtime._current_activity = FusedActivity(  # noqa: SLF001 - focused state test
        ts=now - timedelta(seconds=4),
        activity="WALKING",
        confidence=0.9,
        contributors={"sensor": "WALKING"},
    )
    assert runtime.status(now).data_status == "stale"
    runtime._current_activity = runtime._current_activity.model_copy(update={"ts": now})
    assert runtime.status(now).data_status == "current"
