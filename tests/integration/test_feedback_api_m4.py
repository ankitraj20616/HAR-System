import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from services.feedback_service.app import create_app
from services.feedback_service.config import FeedbackSettings
from services.feedback_service.models import FeedbackContent
from services.runtime import DependencyHealth


@dataclass
class FakeDependency:
    name: str

    async def start(self):
        return None

    async def stop(self):
        return None

    def health(self):
        return DependencyHealth(status="healthy", detail="test")


class SafeProvider:
    def generate(self, _mode, _digest):
        return FeedbackContent(
            headline="Recorded period",
            detail="The supplied period contained recorded walking.",
            severity="info",
            recommendations=["Review the timeline."],
            disclaimer="This automated output is not a medical diagnosis.",
        )


class Activities:
    def between(self, _from, _to, _limit):
        return [
            {
                "ts": datetime(2026, 6, 20, 10, tzinfo=UTC),
                "activity": "WALKING",
                "confidence": 0.9,
            }
        ]

    def trends(self, _from, _to, _cap):
        return [{"activity": "WALKING", "count": 1, "duration_seconds": 5.0}]


class Events:
    def between(self, _from, _to, _limit):
        return []


class Feedbacks:
    def __init__(self):
        self.rows = []

    def add(self, feedback, idempotency_key=None):
        row = feedback.model_dump()
        row.update(payload=feedback.model_dump(mode="json"), idempotency_key=idempotency_key)
        self.rows.append(row)
        return len(self.rows)

    def latest(self, mode=None):
        rows = self.rows if mode is None else [row for row in self.rows if row["mode"] == mode]
        return rows[-1] if rows else None

    def by_idempotency_key(self, key):
        return next((row for row in self.rows if row["idempotency_key"] == key), None)


async def scenario() -> None:
    feedbacks = Feedbacks()
    app = create_app(
        settings=FeedbackSettings(),
        dependencies=(FakeDependency("mqtt"), FakeDependency("database")),
        provider=SafeProvider(),
        activity_repository=Activities(),
        event_repository=Events(),
        feedback_repository=feedbacks,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        empty = await client.get("/api/feedback/latest")
        assert empty.status_code == 200 and empty.json() is None

        generated = await client.post(
            "/api/feedback/generate",
            json={"mode": "summary", "period": "24h", "request_id": "period-1"},
        )
        assert generated.status_code == 200
        assert generated.json()["headline"] == "Recorded period"
        assert generated.json()["fallback"] is False

        replay = await client.post(
            "/api/feedback/generate",
            json={"mode": "summary", "period": "24h", "request_id": "period-1"},
        )
        assert replay.status_code == 200
        assert replay.json()["idempotent_replay"] is True
        assert len(feedbacks.rows) == 1

        latest = await client.get("/api/feedback/latest")
        assert latest.json()["mode"] == "summary"

        invalid = await client.post(
            "/api/feedback/generate", json={"mode": "alert", "period": "forever"}
        )
        assert invalid.status_code == 422


def test_feedback_latest_generate_period_and_idempotency_api() -> None:
    asyncio.run(scenario())
