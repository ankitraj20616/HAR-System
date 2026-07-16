"""Camera construction rules: only buffered network sources get the grabber."""

from typing import Any

from services.video_service.adapters import LatestFrameCamera, build_camera
from services.video_service.config import VideoSettings

NETWORK_SOURCE = "http://192.168.0.145:4747/video"


class StubCamera:
    """Stand-in for OpenCVCamera so tests never touch real hardware."""

    def __init__(self, camera_index: str, fps: float) -> None:
        self.camera_index = camera_index
        self.fps = fps
        self.released = False

    @property
    def is_opened(self) -> bool:
        return True

    def read(self) -> tuple[bool, Any]:
        return True, "frame"

    def release(self) -> None:
        self.released = True


def settings(**overrides: Any) -> VideoSettings:
    defaults: dict[str, Any] = {"camera_index": "0", "video_low_latency": True}
    return VideoSettings(**{**defaults, **overrides})


def test_network_source_is_wrapped_in_the_latest_frame_grabber() -> None:
    camera = build_camera(settings(camera_index=NETWORK_SOURCE), factory=StubCamera)
    try:
        assert isinstance(camera, LatestFrameCamera)
    finally:
        camera.release()


def test_local_webcam_is_not_wrapped() -> None:
    camera = build_camera(settings(camera_index="0"), factory=StubCamera)
    try:
        assert isinstance(camera, StubCamera)
    finally:
        camera.release()


def test_low_latency_capture_can_be_disabled() -> None:
    camera = build_camera(
        settings(camera_index=NETWORK_SOURCE, video_low_latency=False), factory=StubCamera
    )
    try:
        assert isinstance(camera, StubCamera)
    finally:
        camera.release()


def test_configured_source_and_fps_reach_the_inner_camera() -> None:
    camera = build_camera(settings(camera_index=NETWORK_SOURCE, fps=15.0), factory=StubCamera)
    try:
        assert isinstance(camera, LatestFrameCamera)
        assert camera._inner.camera_index == NETWORK_SOURCE
        assert camera._inner.fps == 15.0
    finally:
        camera.release()
