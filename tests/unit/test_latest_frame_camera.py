"""Latest-frame capture behaviour for buffered network camera streams."""

import threading
import time

from services.video_service.adapters import LatestFrameCamera

READ_TIMEOUT = 0.5


class FakeCamera:
    """Scripted camera driven entirely from the grabber thread.

    ``frames`` are handed out one per ``read()``. Once they run out the camera
    either dies or stalls, mirroring the two ways a real stream misbehaves.
    """

    def __init__(self, frames: list[str], *, when_empty: str = "hang") -> None:
        self._frames = frames
        self._when_empty = when_empty
        self._index = 0
        self._unblock = threading.Event()
        # Set when read() is called with nothing left to give. By then every
        # earlier frame has already been stored by the grabber, which makes the
        # tests deterministic without sleeping.
        self.stalled = threading.Event()
        self.released = threading.Event()
        self.opened = True

    @property
    def is_opened(self) -> bool:
        return self.opened

    def read(self) -> tuple[bool, str | None]:
        if self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            return True, frame
        self.stalled.set()
        if self._when_empty == "die":
            return False, None
        self._unblock.wait(timeout=5.0)
        return False, None

    def release(self) -> None:
        self._unblock.set()
        self.released.set()


class EndlessCamera:
    """Camera that always has another frame ready."""

    def __init__(self) -> None:
        self.released = threading.Event()
        self.opened = True

    @property
    def is_opened(self) -> bool:
        return self.opened

    def read(self) -> tuple[bool, str]:
        time.sleep(0.001)
        return True, "frame"

    def release(self) -> None:
        self.released.set()


def test_read_returns_newest_frame_not_oldest() -> None:
    inner = FakeCamera(["frame-1", "frame-2", "frame-3", "frame-4", "frame-5"])
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        assert inner.stalled.wait(timeout=2.0)

        ok, frame = camera.read()

        assert ok is True
        assert frame == "frame-5"
    finally:
        camera.release()


def test_skipped_frames_are_counted_as_dropped() -> None:
    inner = FakeCamera(["frame-1", "frame-2", "frame-3", "frame-4", "frame-5"])
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        assert inner.stalled.wait(timeout=2.0)
        camera.read()

        assert camera.stats()["frames_dropped"] == 4
    finally:
        camera.release()


def test_read_waits_for_a_new_frame_instead_of_repeating_the_last_one() -> None:
    inner = FakeCamera(["frame-1"])
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        assert inner.stalled.wait(timeout=2.0)
        assert camera.read() == (True, "frame-1")

        ok, frame = camera.read()

        assert ok is False
        assert frame is None
    finally:
        camera.release()


def test_read_reports_failure_when_the_stream_dies() -> None:
    inner = FakeCamera([], when_empty="die")
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        assert camera.read() == (False, None)
        assert camera.is_opened is False
    finally:
        camera.release()


def test_read_times_out_on_a_stalled_stream() -> None:
    inner = FakeCamera([])
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        started = time.monotonic()

        assert camera.read() == (False, None)

        assert time.monotonic() - started >= READ_TIMEOUT
    finally:
        camera.release()


def test_frame_slot_is_cleared_once_the_frame_is_handed_over() -> None:
    inner = FakeCamera(["frame-1"])
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        assert inner.stalled.wait(timeout=2.0)
        camera.read()

        assert camera.stats()["frames_held"] == 0
    finally:
        camera.release()


def test_release_drops_any_frame_still_held() -> None:
    inner = FakeCamera(["frame-1"])
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    assert inner.stalled.wait(timeout=2.0)

    camera.release()

    assert camera.stats()["frames_held"] == 0


def test_release_stops_the_grabber_thread_and_releases_the_inner_camera() -> None:
    inner = EndlessCamera()
    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)

    camera.release()

    assert camera.is_running is False
    assert inner.released.is_set()


def test_unopened_camera_never_starts_a_grabber_thread() -> None:
    inner = EndlessCamera()
    inner.opened = False

    camera = LatestFrameCamera(inner, read_timeout=READ_TIMEOUT)
    try:
        assert camera.is_opened is False
        assert camera.is_running is False
    finally:
        camera.release()
