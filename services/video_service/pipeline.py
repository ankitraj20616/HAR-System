"""Resource-safe, FPS-paced webcam-to-prediction pipeline."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from services.runtime import DependencyHealth
from services.video_service.classifier import ActivityClassifier
from services.video_service.config import VideoSettings
from services.video_service.landmarks import PoseLandmarks
from shared.labels import Modality
from shared.logging import get_logger
from shared.schemas import VideoPrediction

logger = get_logger(__name__)


class Camera(Protocol):
    @property
    def is_opened(self) -> bool: ...

    def read(self) -> tuple[bool, Any]: ...

    def release(self) -> None: ...


class PoseEstimator(Protocol):
    def estimate(self, frame: Any) -> PoseLandmarks | None: ...

    def close(self) -> None: ...


class PredictionPublisher(Protocol):
    def publish(self, prediction: VideoPrediction) -> None: ...


class VideoPipeline:
    """Managed dependency with injectable camera, pose, clock, and publisher."""

    name = "video"

    def __init__(
        self,
        settings: VideoSettings,
        publisher: PredictionPublisher,
        camera_factory: Callable[[], Camera],
        estimator_factory: Callable[[], PoseEstimator],
        *,
        monotonic: Callable[[], float] = time.monotonic,
        run_blocking: Callable[..., Awaitable[Any]] = asyncio.to_thread,
    ) -> None:
        self.settings = settings
        self.publisher = publisher
        self.camera_factory = camera_factory
        self.estimator_factory = estimator_factory
        self.monotonic = monotonic
        self.run_blocking = run_blocking
        self.classifier = ActivityClassifier(settings)
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._camera: Camera | None = None
        self._estimator: PoseEstimator | None = None
        self._last_timestamp: datetime | None = None
        self._health = DependencyHealth(status="starting", detail="video pipeline not started")

    async def start(self) -> None:
        self._stop.clear()
        self._health = DependencyHealth(status="starting", detail="opening configured camera")
        self._task = asyncio.create_task(self._run(), name="video-capture-pipeline")
        await asyncio.sleep(0)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._close_resources()
        self._health = DependencyHealth(status="stopped", detail="camera released")

    def health(self) -> DependencyHealth:
        return self._health

    async def process_frame(self, frame: Any) -> VideoPrediction:
        """Process one borrowed frame; only its derived numeric prediction escapes."""

        if self._estimator is None:
            raise RuntimeError("pose estimator is not open")
        pose = await self.run_blocking(self._estimator.estimate, frame)
        result = self.classifier.classify(pose)
        prediction = VideoPrediction(
            ts=self._next_timestamp(),
            modality=Modality.VIDEO,
            label=result.label,
            confidence=result.confidence,
            orientation=result.orientation,
        )
        self.publisher.publish(prediction)
        return prediction

    def _next_timestamp(self) -> datetime:
        """Keep wire timestamps strictly ordered even if the wall clock adjusts."""

        timestamp = datetime.now(UTC)
        if self._last_timestamp is not None and timestamp <= self._last_timestamp:
            timestamp = self._last_timestamp + timedelta(microseconds=1)
        self._last_timestamp = timestamp
        return timestamp

    async def _run(self) -> None:
        attempts = 0
        backoff = self.settings.reconnect_initial_backoff
        try:
            while not self._stop.is_set():
                try:
                    await self._open_resources()
                    await self._capture_until_failure()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    attempts += 1
                    self._health = DependencyHealth(
                        status="degraded",
                        detail=f"camera/pose pipeline unavailable ({type(exc).__name__})",
                    )
                    logger.warning(
                        "Video pipeline unavailable; retry scheduled",
                        extra={"event": "video_pipeline_retry", "attempt": attempts},
                    )
                    await self._close_resources()
                    if attempts >= self.settings.reconnect_attempts:
                        logger.error(
                            "Video reconnect limit reached; API remains available",
                            extra={"event": "video_reconnect_exhausted"},
                        )
                        return
                    await asyncio.sleep(backoff)
                    backoff = min(self.settings.reconnect_max_backoff, max(backoff * 2.0, 0.01))
        finally:
            await self._close_resources()

    async def _open_resources(self) -> None:
        await self._close_resources()
        camera = await self.run_blocking(self.camera_factory)
        if not camera.is_opened:
            camera.release()
            raise ConnectionError("configured camera could not be opened")
        try:
            estimator = await self.run_blocking(self.estimator_factory)
        except Exception:
            camera.release()
            raise
        self._camera = camera
        self._estimator = estimator
        self._health = DependencyHealth(
            status="healthy",
            detail=f"processing camera at {self.settings.fps:g} FPS",
        )

    async def _capture_until_failure(self) -> None:
        interval = 1.0 / self.settings.fps
        deadline = self.monotonic()
        while not self._stop.is_set():
            camera = self._camera
            if camera is None:
                raise ConnectionError("camera closed")
            ok, frame = await self.run_blocking(camera.read)
            if not ok or frame is None:
                raise ConnectionError("camera frame read failed")
            try:
                await self.process_frame(frame)
            finally:
                # Privacy boundary: release the sole local reference immediately.
                del frame
            deadline += interval
            await asyncio.sleep(max(0.0, deadline - self.monotonic()))

    async def _close_resources(self) -> None:
        camera, self._camera = self._camera, None
        estimator, self._estimator = self._estimator, None
        if estimator is not None:
            with suppress(Exception):
                await self.run_blocking(estimator.close)
        if camera is not None:
            with suppress(Exception):
                await self.run_blocking(camera.release)
