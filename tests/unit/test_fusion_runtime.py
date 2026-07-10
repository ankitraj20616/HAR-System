import asyncio
from datetime import UTC, datetime, timedelta

from services.fusion_service.config import FusionSettings
from services.fusion_service.runtime import FusionMQTTDependency
from shared.schemas import SensorPrediction, VideoPrediction
from shared.topics import SENSOR_PREDICTION, VIDEO_PREDICTION


class RecordingRepository:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.items = []

    def add(self, item):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("offline")
        self.items.append(item)
        return len(self.items)


class FakeClient:
    def __init__(self) -> None:
        self.subscriptions = []
        self.publications = []

    def subscribe(self, topic, qos):
        self.subscriptions.append((topic, qos))

    def publish(self, topic, payload, qos, retain):
        self.publications.append((topic, payload, qos, retain))
        return type("Result", (), {"rc": 0})()


def prediction_pair(ts: datetime):
    return (
        SensorPrediction(
            ts=ts,
            modality="sensor",
            label="LYING",
            confidence=0.9,
            motion_intensity=3.0,
        ),
        VideoPrediction(
            ts=ts + timedelta(milliseconds=50),
            modality="video",
            label="LYING",
            confidence=0.8,
            orientation="horizontal",
        ),
    )


def test_reconnect_subscribes_to_both_qos1_inputs() -> None:
    runtime = FusionMQTTDependency(FusionSettings())
    client = FakeClient()

    runtime._on_connect(client, None, None, 0)  # type: ignore[attr-defined]
    runtime._on_connect(client, None, None, 0)  # type: ignore[attr-defined]

    assert client.subscriptions == [
        (SENSOR_PREDICTION, 1),
        (VIDEO_PREDICTION, 1),
        (SENSOR_PREDICTION, 1),
        (VIDEO_PREDICTION, 1),
    ]


def test_runtime_persists_before_publish_and_retries_database_failure() -> None:
    async def scenario() -> None:
        activity_repo = RecordingRepository(failures=1)
        event_repo = RecordingRepository()
        settings = FusionSettings(
            smoothing_window=1,
            fall_accel_threshold=2.5,
            alignment_tolerance_ms=1500,
        )
        runtime = FusionMQTTDependency(
            settings,
            activity_repository=activity_repo,  # type: ignore[arg-type]
            event_repository=event_repo,  # type: ignore[arg-type]
        )
        client = FakeClient()
        runtime._client = client  # type: ignore[attr-defined]
        runtime._connected.set()  # type: ignore[attr-defined]
        timestamp = datetime(2026, 6, 20, 10, tzinfo=UTC)
        sensor, video = prediction_pair(timestamp)

        await runtime.process_prediction(sensor)
        await runtime.process_prediction(video)
        assert len(event_repo.items) == 1
        assert event_repo.items[0].type == "FALL"

        await runtime.process_interval(timestamp + timedelta(seconds=1))
        assert activity_repo.items == []
        # The fall was publishable, but the activity is held while DB is unavailable.
        assert all(publication[0] != "har/activity" for publication in client.publications)

        await runtime._retry_pending()  # type: ignore[attr-defined]
        assert len(activity_repo.items) == 1
        assert any(publication[0] == "har/activity" for publication in client.publications)
        assert runtime.status(timestamp + timedelta(seconds=1)).activity == "LYING"

    asyncio.run(scenario())
