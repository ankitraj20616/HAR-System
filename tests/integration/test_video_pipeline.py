"""Capture/publish lifecycle tests using camera and pose test doubles."""

from __future__ import annotations

import asyncio
from typing import Any

from services.video_service.config import VideoSettings
from services.video_service.pipeline import VideoPipeline
from shared.labels import ActivityLabel, Orientation
from tests.unit.test_video_classifier import standing_pose, standing_pose_at


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


class FakeStatsCamera(FakeCamera):
    """Stands in for LatestFrameCamera, which reports capture counters."""

    def stats(self) -> dict[str, int]:
        return {"frames_captured": 10, "frames_dropped": 4, "frames_held": 0}


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


def test_pipeline_retries_forever_until_the_camera_comes_back() -> None:
    async def scenario() -> None:
        published = asyncio.Event()

        class SignallingPublisher(FakePublisher):
            def publish(self, prediction) -> None:
                super().publish(prediction)
                published.set()

        cameras = [
            FakeCamera([], opened=False),
            FakeCamera([], opened=False),
            FakeCamera([object()]),
        ]
        publisher = SignallingPublisher()
        settings = VideoSettings(
            fps=60,
            reconnect_attempts=0,
            reconnect_initial_backoff=0,
        )
        pipeline = VideoPipeline(
            settings,
            publisher,
            camera_factory=lambda: cameras.pop(0) if cameras else FakeCamera([], opened=False),
            estimator_factory=lambda: FakeEstimator(standing_pose()),
            run_blocking=run_immediately,
        )
        await pipeline.start()
        await asyncio.wait_for(published.wait(), timeout=5)
        await pipeline.stop()

        assert publisher.predictions[0].label == ActivityLabel.STANDING

    asyncio.run(scenario())


def test_health_reports_capture_counters_when_the_camera_tracks_them() -> None:
    async def scenario() -> None:
        pipeline = VideoPipeline(
            VideoSettings(),
            FakePublisher(),
            camera_factory=lambda: FakeStatsCamera([object()]),
            estimator_factory=lambda: FakeEstimator(standing_pose()),
            run_blocking=run_immediately,
        )
        await pipeline._open_resources()

        health = pipeline.health()

        assert health.status == "healthy"
        assert "dropped=4" in health.detail
        assert "captured=10" in health.detail
        await pipeline.stop()

    asyncio.run(scenario())


def test_health_omits_capture_counters_for_a_plain_camera() -> None:
    async def scenario() -> None:
        pipeline = VideoPipeline(
            VideoSettings(),
            FakePublisher(),
            camera_factory=lambda: FakeCamera([object()]),
            estimator_factory=lambda: FakeEstimator(standing_pose()),
            run_blocking=run_immediately,
        )
        await pipeline._open_resources()

        health = pipeline.health()

        assert health.status == "healthy"
        assert "dropped" not in health.detail
        await pipeline.stop()

    asyncio.run(scenario())


def test_pipeline_publishes_the_downward_velocity_of_a_dropping_body() -> None:
    async def scenario() -> None:
        class SequenceEstimator(FakeEstimator):
            def __init__(self, poses) -> None:
                super().__init__(None)
                self.poses = poses

            def estimate(self, frame: Any):
                return self.poses.pop(0)

        poses = [standing_pose_at(0.0)] * 3
        poses += [standing_pose_at(0.06 * step) for step in range(1, 5)]
        estimator = SequenceEstimator(poses)
        publisher = FakePublisher()
        pipeline = VideoPipeline(
            VideoSettings(fps=10.0),
            publisher,
            camera_factory=lambda: FakeCamera([]),
            estimator_factory=lambda: estimator,
            run_blocking=run_immediately,
        )
        pipeline._estimator = estimator

        for _ in range(len(poses)):
            await pipeline.process_frame(object())

        assert publisher.predictions[0].vertical_velocity == 0.0
        assert publisher.predictions[-1].vertical_velocity > 0.3

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
