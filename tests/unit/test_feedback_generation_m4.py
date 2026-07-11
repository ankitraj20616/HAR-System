import asyncio
from datetime import UTC, datetime

from services.feedback_service.config import FeedbackSettings
from services.feedback_service.digest import build_digest
from services.feedback_service.engine import FeedbackEngine
from services.feedback_service.models import FeedbackContent
from services.feedback_service.runtime import FeedbackRuntime
from shared.schemas import HAREvent

SAFE = {
    "headline": "Recent activity",
    "detail": "Recorded walking was present in this period.",
    "severity": "info",
    "recommendations": ["Review the recorded timeline."],
    "disclaimer": "This is assistive information, not a medical diagnosis.",
}


class SequenceProvider:
    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    def generate(self, mode, digest):
        self.calls.append((mode, digest))
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_provider_is_repaired_once_and_safe_output_is_accepted() -> None:
    provider = SequenceProvider(
        [
            {**SAFE, "detail": "The patient has a stroke."},
            FeedbackContent.model_validate(SAFE),
        ]
    )
    result = asyncio.run(
        FeedbackEngine(provider).generate(
            "feedback",
            {"activity_durations_seconds": {"WALKING": 12}, "sample_count": 1},
        )
    )
    assert result.fallback_used is False
    assert result.feedback.headline == "Recent activity"
    assert len(provider.calls) == 2
    assert "repair_instruction" in provider.calls[1][1]


def test_two_invalid_attempts_use_grounded_deterministic_fallback() -> None:
    provider = SequenceProvider([ValueError("bad JSON"), ValueError("still bad")])
    result = asyncio.run(
        FeedbackEngine(provider).generate(
            "summary",
            {"activity_durations_seconds": {}, "sample_count": 0, "events": []},
        )
    )
    assert result.fallback_used is True
    assert result.provider_status == "fallback"
    assert result.feedback.headline == "No activity data for this period"
    assert "not a medical diagnosis" in result.feedback.disclaimer
    assert len(provider.calls) == 2


def test_digest_aggregates_facts_and_excludes_raw_private_data() -> None:
    start = datetime(2026, 6, 20, 10, tzinfo=UTC)
    end = datetime(2026, 6, 20, 10, 1, tzinfo=UTC)
    digest = build_digest(
        start,
        end,
        [
            {
                "ts": start,
                "activity": "WALKING",
                "raw_frame": "must-not-leak",
                "landmarks": [1, 2],
            }
        ],
        [],
        maximum_size=4096,
    )
    assert digest["activity_durations_seconds"] == {"WALKING": 5.0}
    text = str(digest)
    assert "must-not-leak" not in text
    assert "landmarks" not in text


class EmptyRepo:
    def between(self, *_args):
        return []

    def trends(self, *_args):
        return []


class MemoryFeedbackRepo:
    def __init__(self):
        self.rows = []

    def add(self, feedback, idempotency_key=None):
        self.rows.append(
            {
                **feedback.model_dump(),
                "payload": feedback.model_dump(mode="json"),
                "idempotency_key": idempotency_key,
            }
        )
        return len(self.rows)

    def by_idempotency_key(self, key):
        return next((row for row in self.rows if row["idempotency_key"] == key), None)


class UnavailableFeedbackRepo:
    def add(self, *_args):
        raise RuntimeError("database unavailable")

    def by_idempotency_key(self, _key):
        raise RuntimeError("database unavailable")


class RecordingHub:
    def __init__(self):
        self.envelopes = []

    async def broadcast(self, envelope):
        self.envelopes.append(envelope)

    async def close(self):
        return None


def test_critical_event_template_is_immediate_and_idempotent() -> None:
    feedbacks = MemoryFeedbackRepo()
    hub = RecordingHub()
    runtime = FeedbackRuntime(
        FeedbackSettings(),
        provider=SequenceProvider([AssertionError("provider must not delay alert")]),
        activity_repository=EmptyRepo(),
        event_repository=EmptyRepo(),
        feedback_repository=feedbacks,
        websocket_hub=hub,
    )
    event = HAREvent(
        ts="2026-06-20T10:00:00Z",
        type="FALL",
        severity="critical",
        confidence=0.93,
        evidence={"motion_intensity": 0.95, "orientation": "horizontal"},
    )

    async def scenario():
        first = await runtime.process_event(event)
        second = await runtime.process_event(event)
        assert first == second

    asyncio.run(scenario())
    assert len(feedbacks.rows) == 1
    assert feedbacks.rows[0]["idempotency_key"].startswith("event:FALL:")
    assert len(hub.envelopes) == 1
    assert hub.envelopes[0].data.severity == "critical"
    assert runtime.counters["duplicates"] == 1


def test_critical_event_is_published_and_queued_when_database_is_down() -> None:
    hub = RecordingHub()
    runtime = FeedbackRuntime(
        FeedbackSettings(),
        provider=SequenceProvider([]),
        activity_repository=EmptyRepo(),
        event_repository=EmptyRepo(),
        feedback_repository=UnavailableFeedbackRepo(),
        websocket_hub=hub,
    )
    event = HAREvent(
        ts="2026-06-20T10:00:00Z",
        type="FALL",
        severity="critical",
        confidence=0.93,
        evidence={"motion_intensity": 0.95, "orientation": "horizontal"},
    )

    result = asyncio.run(runtime.process_event(event))

    assert result.severity == "critical"
    assert len(hub.envelopes) == 1
    assert runtime._pending_feedback  # noqa: SLF001 - verifies safety outbox behavior
    assert runtime.health().status == "degraded"


def test_full_event_queue_applies_backpressure_without_dropping_alert() -> None:
    runtime = FeedbackRuntime(
        FeedbackSettings(),
        provider=SequenceProvider([]),
        activity_repository=EmptyRepo(),
        event_repository=EmptyRepo(),
        feedback_repository=MemoryFeedbackRepo(),
    )
    first = HAREvent(
        ts="2026-06-20T10:00:00Z",
        type="FALL",
        severity="critical",
        confidence=0.9,
        evidence={},
    )
    second = first.model_copy(update={"ts": datetime(2026, 6, 20, 10, 1, tzinfo=UTC)})

    async def scenario():
        runtime._queue = asyncio.Queue(maxsize=1)  # noqa: SLF001
        runtime._queue.put_nowait(first)  # noqa: SLF001
        runtime._enqueue(second)  # noqa: SLF001
        assert runtime.counters["queue_backpressure"] == 1
        assert await runtime._queue.get() == first  # noqa: SLF001
        await asyncio.sleep(0)
        assert await runtime._queue.get() == second  # noqa: SLF001

    asyncio.run(scenario())
