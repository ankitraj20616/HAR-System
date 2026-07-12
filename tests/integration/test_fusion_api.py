import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from services.fusion_service.app import create_app
from services.fusion_service.config import FusionSettings
from services.fusion_service.runtime import FusionMQTTDependency
from services.runtime import DependencyHealth


@dataclass
class FakeDependency:
    name: str

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def health(self) -> DependencyHealth:
        return DependencyHealth(status="healthy", detail="test")


class ActivityRepo:
    def __init__(self) -> None:
        self.items = [
            {
                "id": 1,
                "ts": datetime(2026, 6, 20, 10, tzinfo=UTC),
                "activity": "WALKING",
                "confidence": 0.9,
                "sensor_label": "WALKING",
                "video_label": "WALKING",
            }
        ]

    def add(self, _activity):
        return 1

    def between(self, _from, _to, _limit):
        return self.items

    def trends(self, _from, _to, _cap):
        return [{"activity": "WALKING", "count": 2, "duration_seconds": 2.0}]


class EventRepo:
    def __init__(self) -> None:
        self.item = {
            "id": 7,
            "ts": datetime(2026, 6, 20, 10, tzinfo=UTC),
            "type": "FALL",
            "severity": "critical",
            "confidence": 0.9,
            "evidence": {"rule": "test"},
            "acknowledged": False,
        }

    def add(self, _event):
        return 7

    def between(self, _from, _to, _limit):
        return [self.item]

    def acknowledge(self, event_id):
        if event_id != self.item["id"]:
            return False
        self.item["acknowledged"] = True
        return True

    def get(self, event_id):
        return self.item if event_id == self.item["id"] else None


async def request_scenario() -> None:
    settings = FusionSettings()
    activity_repo = ActivityRepo()
    event_repo = EventRepo()
    runtime = FusionMQTTDependency(
        settings,
        activity_repository=activity_repo,  # type: ignore[arg-type]
        event_repository=event_repo,  # type: ignore[arg-type]
    )
    app = create_app(
        settings=settings,
        dependencies=(FakeDependency("mqtt"), FakeDependency("database")),
        fusion_runtime=runtime,
        activity_repository=activity_repo,  # type: ignore[arg-type]
        event_repository=event_repo,  # type: ignore[arg-type]
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        status_response = await client.get("/api/status")
        assert status_response.status_code == 200
        assert status_response.json()["activity"] == "UNKNOWN"
        assert status_response.json()["modality_health"]["sensor"]["status"] == "offline"

        timeline = await client.get(
            "/api/timeline",
            params={"from": "2026-06-20T00:00:00Z", "to": "2026-06-21T00:00:00Z"},
        )
        assert timeline.status_code == 200
        assert timeline.json()["items"][0]["activity"] == "WALKING"

        events = await client.get("/api/events")
        assert events.status_code == 200
        assert events.json()["items"][0]["acknowledged"] is False

        trends = await client.get("/api/trends", params={"period": "24h"})
        assert trends.status_code == 200
        walking = next(
            item for item in trends.json()["activities"] if item["activity"] == "WALKING"
        )
        assert walking == {"activity": "WALKING", "count": 2, "duration_seconds": 2.0}

        first_ack = await client.post("/api/events/7/ack")
        second_ack = await client.post("/api/events/7/ack")
        missing_ack = await client.post("/api/events/8/ack")
        assert first_ack.status_code == second_ack.status_code == 200
        assert second_ack.json()["acknowledged"] is True
        assert missing_ack.status_code == 404

        invalid_range = await client.get(
            "/api/timeline",
            params={"from": "2026-06-21T00:00:00Z", "to": "2026-06-20T00:00:00Z"},
        )
        non_utc = await client.get(
            "/api/events",
            params={"from": "2026-06-20T05:30:00+05:30"},
        )
        invalid_period = await client.get("/api/trends", params={"period": "forever"})
        assert invalid_range.status_code == 422
        assert non_utc.status_code == 422
        assert invalid_period.status_code == 422


def test_fusion_history_status_trends_and_idempotent_ack_api() -> None:
    asyncio.run(request_scenario())
