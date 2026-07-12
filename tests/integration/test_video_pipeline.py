"""Capture/publish lifecycle tests using camera and pose test doubles."""

from __future__ import annotations

import asyncio
from typing import Any

from services.video_service.config import VideoSettings
from services.video_service.pipeline import VideoPipeline
from shared.labels import ActivityLabel, Orientation
from tests.unit.test_video_classifier import standing_pose


async def run_immediately(function, *args):
    return function(*args)


class FakeCamera:
    def __init__(self, frames: list[Any], opened: bool = True) -> None:
        self.frames = frames
        self.is_opened = opened
        self.released = False

    def read(self) -> tuple[bool, Any]:
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self) -> None:
        self.released = True


class FakeEstimator:
    def __init__(self, pose) -> None:
        self.pose = pose
        self.closed = False
        self.seen_ids: list[int] = []

    def estimate(self, frame: Any):
        self.seen_ids.append(id(frame))
        return self.pose

    def close(self) -> None:
        self.closed = True


class FakePublisher:
    def __init__(self) -> None:
        self.predictions = []

    def publish(self, prediction) -> None:
        self.predictions.append(prediction)


def test_pipeline_publishes_contract_and_releases_resources_after_read_failure() -> None:
    async def scenario() -> None:
        marker = object()
        camera = FakeCamera([marker])
        estimator = FakeEstimator(standing_pose())
        publisher = FakePublisher()
        settings = VideoSettings(
            fps=60,
            reconnect_attempts=1,
            reconnect_initial_backoff=0,
        )
        pipeline = VideoPipeline(
            settings,
            publisher,
            camera_factory=lambda: camera,
            estimator_factory=lambda: estimator,
            run_blocking=run_immediately,
        )
        await pipeline.start()
        assert pipeline._task is not None
        await pipeline._task
        assert camera.released is True
        assert estimator.closed is True
        assert estimator.seen_ids == [id(marker)]
        assert len(publisher.predictions) == 1
        prediction = publisher.predictions[0]
        assert prediction.label == ActivityLabel.STANDING
        assert prediction.orientation == Orientation.VERTICAL
        assert prediction.modality == "video"
        assert pipeline.health().status == "degraded"
        await pipeline.stop()

    asyncio.run(scenario())


def test_pipeline_no_person_publishes_unknown_and_keeps_processing() -> None:
    async def scenario() -> None:
        camera = FakeCamera([])
        estimator = FakeEstimator(None)
        publisher = FakePublisher()
        pipeline = VideoPipeline(
            VideoSettings(),
            publisher,
            camera_factory=lambda: camera,
            estimator_factory=lambda: estimator,
            run_blocking=run_immediately,
        )
        pipeline._estimator = estimator
        prediction = await pipeline.process_frame(object())
        assert prediction.label == ActivityLabel.UNKNOWN
        assert prediction.orientation == Orientation.UNKNOWN
        assert prediction.confidence <= 0.1
        assert publisher.predictions == [prediction]

    asyncio.run(scenario())
