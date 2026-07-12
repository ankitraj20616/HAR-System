"""In-process replay-to-sensor flow; MQTT transport is replaced at its publish boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from services.sensor_service.config import SensorSettings
from services.sensor_service.pipeline import SensorPipeline
from shared.schemas import SensorPrediction
from shared.topics import SENSOR_RAW
from simulator.datasets import DatasetWindow
from simulator.replay import ReplayEngine, ReplayOptions


class FixedClock:
    def monotonic(self) -> float:
        return 0.0

    def sleep(self, _seconds: float) -> None:
        raise AssertionError("non-real-time replay must not sleep")

    def utcnow(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)


class PipelinePublisher:
    def __init__(self, pipeline: SensorPipeline) -> None:
        self.pipeline = pipeline
        self.predictions: list[SensorPrediction] = []
        self.payloads: list[str] = []

    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> Any:
        assert (topic, qos, retain) == (SENSOR_RAW, 0, False)
        self.payloads.append(payload)
        self.predictions.extend(self.pipeline.process_json(payload))
        return None


def test_labelled_replay_drives_ordered_sensor_predictions_without_label_leakage() -> None:
    settings = SensorSettings(window_size=20, window_overlap=0.5, use_fallback=True)
    pipeline = SensorPipeline(settings)
    pipeline.start()
    publisher = PipelinePublisher(pipeline)
    samples = tuple((0.0, 0.0, 1.0) for _ in range(40))
    source = [
        DatasetWindow(
            timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            sampling_hz=20,
            accel=samples,
            gyro=((0.0, 0.0, 0.0),) * 40,
            source_label="LAYING",
            scenario_id="evaluation-only-label",
        )
    ]

    stats = ReplayEngine(
        source,  # type: ignore[arg-type]
        publisher,
        options=ReplayOptions(realtime=False),
        clock=FixedClock(),
    ).run()

    assert stats.published == 1
    assert len(publisher.predictions) == 3
    assert [prediction.ts for prediction in publisher.predictions] == sorted(
        prediction.ts for prediction in publisher.predictions
    )
    assert "evaluation-only-label" not in publisher.payloads[0]
    assert "LAYING" not in publisher.payloads[0]
