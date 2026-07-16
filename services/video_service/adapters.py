"""Optional local camera, pose, and MQTT adapters.

Heavy vision packages are imported lazily so geometry tests and API health can
run on systems without a webcam or MediaPipe installation.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import suppress
from typing import Any, Protocol

from services.runtime import MQTTDependency
from services.video_service.config import VideoSettings
from services.video_service.landmarks import Landmark, PoseLandmarks
from shared.logging import get_logger
from shared.schemas import VideoPrediction
from shared.topics import VIDEO_PREDICTION, policy_for

logger = get_logger(__name__)


class _Camera(Protocol):
    @property
    def is_opened(self) -> bool: ...

    def read(self) -> tuple[bool, Any]: ...

    def release(self) -> None: ...


def is_network_source(camera_index: str) -> bool:
    """Network streams are URLs; local webcams are plain device numbers."""

    return not camera_index.isdigit()


class OpenCVCamera:
    """Small capture adapter with no recording or image-writing API."""

    def __init__(self, camera_index: str, fps: float) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required for webcam capture") from exc

        # If the string is just a number (e.g. "0"), parse it to int for local devices
        target_index = int(camera_index) if camera_index.isdigit() else camera_index
        self._capture = cv2.VideoCapture(target_index)
        self._capture.set(cv2.CAP_PROP_FPS, fps)
        # Honoured by V4L2/DSHOW webcams. FFmpeg network streams ignore it, which
        # is why those are wrapped in LatestFrameCamera instead.
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    @property
    def is_opened(self) -> bool:
        return bool(self._capture.isOpened())

    def read(self) -> tuple[bool, Any]:
        return self._capture.read()

    def release(self) -> None:
        self._capture.release()


class LatestFrameCamera:
    """Keep only the newest frame of a buffered network stream.

    Network sources deliver frames faster than the pose pipeline consumes them.
    Unread frames queue up in the OS socket buffer, so ``read()`` on the inner
    camera hands back progressively older frames and latency never recovers. A
    grabber thread drains the stream at its native rate and keeps just the most
    recent frame, so the backlog cannot form.

    Privacy: at most one frame is held, it is replaced in place, and it is
    dropped as soon as the pipeline takes it. Nothing is encoded or persisted.

    Thread ownership: the grabber thread is the only owner of the inner camera.
    It reads it and releases it, so the inner camera is never touched while
    another thread is mid-read.
    """

    def __init__(self, inner: _Camera, *, read_timeout: float = 5.0) -> None:
        self._inner = inner
        self._read_timeout = read_timeout
        self._new_frame = threading.Condition()
        self._frame: Any = None
        self._seq = 0
        self._last_returned = 0
        self._dropped = 0
        self._failed = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # Check before starting the thread; afterwards the inner camera belongs
        # to the grabber alone.
        self._opened = inner.is_opened
        if not self._opened:
            return
        self._thread = threading.Thread(
            target=self._drain, name="video-frame-grabber", daemon=True
        )
        self._thread.start()

    @property
    def is_opened(self) -> bool:
        with self._new_frame:
            return self._opened and not self._failed

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _drain(self) -> None:
        """Read at the stream's own rate, keeping only the newest frame."""

        try:
            while not self._stop.is_set():
                ok, frame = self._inner.read()
                with self._new_frame:
                    if not ok or frame is None:
                        self._failed = True
                        self._new_frame.notify_all()
                        return
                    if self._seq > self._last_returned:
                        # The previous frame is going out unprocessed; that is
                        # the point, but it is worth counting.
                        self._dropped += 1
                    self._frame = frame
                    self._seq += 1
                    self._new_frame.notify_all()
        finally:
            with suppress(Exception):
                self._inner.release()

    def read(self) -> tuple[bool, Any]:
        """Return the newest unseen frame, or fail so the pipeline reconnects."""

        with self._new_frame:
            fresh = self._new_frame.wait_for(
                lambda: self._seq > self._last_returned or self._failed,
                timeout=self._read_timeout,
            )
            if self._failed or not fresh:
                return False, None
            self._last_returned = self._seq
            frame, self._frame = self._frame, None
            return True, frame

    def stats(self) -> dict[str, int]:
        with self._new_frame:
            return {
                "frames_captured": self._seq,
                "frames_dropped": self._dropped,
                "frames_held": 0 if self._frame is None else 1,
            }

    def release(self) -> None:
        self._stop.set()
        with self._new_frame:
            # Privacy boundary: never keep a frame alive past shutdown.
            self._frame = None
        thread = self._thread
        if thread is None:
            # No grabber ever ran, so nobody else owns the inner camera.
            with suppress(Exception):
                self._inner.release()
            return
        thread.join(timeout=self._read_timeout + 1.0)
        if thread.is_alive():
            # Daemon thread; it exits with the process once its blocking read
            # returns, and it releases the inner camera on the way out.
            logger.warning(
                "Video grabber thread did not stop in time",
                extra={"event": "video_grabber_stop_timeout"},
            )


def build_camera(
    settings: VideoSettings,
    *,
    factory: Callable[[str, float], _Camera] = OpenCVCamera,
) -> _Camera:
    """Open the configured camera, adding the grabber only where it helps."""

    camera = factory(settings.camera_index, settings.fps)
    if settings.video_low_latency and is_network_source(settings.camera_index):
        return LatestFrameCamera(camera, read_timeout=settings.capture_read_timeout)
    return camera


class MediaPipePoseEstimator:
    """Convert MediaPipe's result immediately into numeric landmark objects."""

    def __init__(self, min_visibility: float) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("mediapipe is required for local pose estimation") from exc
        self._mp = mp
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=min_visibility,
            min_tracking_confidence=min_visibility,
        )

    def estimate(self, frame: Any) -> PoseLandmarks | None:
        # Conversion is kept here; neither the result object nor the frame is retained.
        cv2 = __import__("cv2")
        result = self._pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if result.pose_landmarks is None:
            return None
        pose_landmark = self._mp.solutions.pose.PoseLandmark
        wanted = {
            "left_shoulder": pose_landmark.LEFT_SHOULDER,
            "right_shoulder": pose_landmark.RIGHT_SHOULDER,
            "left_hip": pose_landmark.LEFT_HIP,
            "right_hip": pose_landmark.RIGHT_HIP,
            "left_knee": pose_landmark.LEFT_KNEE,
            "right_knee": pose_landmark.RIGHT_KNEE,
            "left_ankle": pose_landmark.LEFT_ANKLE,
            "right_ankle": pose_landmark.RIGHT_ANKLE,
            "left_wrist": pose_landmark.LEFT_WRIST,
            "right_wrist": pose_landmark.RIGHT_WRIST,
        }
        return PoseLandmarks(
            {
                name: Landmark(
                    x=result.pose_landmarks.landmark[index].x,
                    y=result.pose_landmarks.landmark[index].y,
                    z=result.pose_landmarks.landmark[index].z,
                    visibility=result.pose_landmarks.landmark[index].visibility,
                )
                for name, index in wanted.items()
            }
        )

    def close(self) -> None:
        with suppress(Exception):
            self._pose.close()


class VideoMQTTPublisher(MQTTDependency):
    """Managed MQTT connection that only accepts the strict video contract."""

    def publish(self, prediction: VideoPrediction) -> None:
        client = self._client
        if client is None:
            raise ConnectionError("MQTT publisher is not started")
        policy = policy_for(VIDEO_PREDICTION)
        result = client.publish(
            policy.topic,
            payload=prediction.model_dump_json(),
            qos=policy.qos,
            retain=policy.retain,
        )
        result_code = getattr(result, "rc", 0)
        if result_code != 0:
            raise ConnectionError(f"MQTT publish failed with code {result_code}")
