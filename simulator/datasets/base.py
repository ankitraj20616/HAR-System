"""Common contracts and validation for simulator dataset loaders."""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from shared.labels import ActivityLabel, map_activity_label

Vector3 = tuple[float, float, float]


class DatasetError(ValueError):
    """Base error raised for unusable simulator data."""


class DatasetFormatError(DatasetError):
    """A dataset file does not match the documented source format."""


@dataclass(frozen=True, slots=True)
class DatasetWindow:
    """One source-labelled, fixed-rate IMU window.

    ``source_label`` and ``scenario_id`` are evaluation metadata. Replay code
    deliberately keeps them out of the raw sensor payload.
    """

    timestamp: datetime
    sampling_hz: float
    accel: tuple[Vector3, ...]
    gyro: tuple[Vector3, ...]
    source_label: str
    scenario_id: str
    stride_samples: int | None = None
    stream_id: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise DatasetFormatError("window timestamp must be timezone-aware")
        if self.timestamp.utcoffset() != UTC.utcoffset(self.timestamp):
            raise DatasetFormatError("window timestamp must use UTC")
        if not math.isfinite(self.sampling_hz) or self.sampling_hz <= 0:
            raise DatasetFormatError("sampling_hz must be a positive finite number")
        if not self.accel or len(self.accel) != len(self.gyro):
            raise DatasetFormatError("accel and gyro must have equal, non-zero sample counts")
        if not self.source_label.strip():
            raise DatasetFormatError("source_label cannot be empty")
        if not self.scenario_id.strip():
            raise DatasetFormatError("scenario_id cannot be empty")
        stride = self.stride_samples if self.stride_samples is not None else len(self.accel)
        if not 0 < stride <= len(self.accel):
            raise DatasetFormatError(
                "stride_samples must be positive and no larger than the window"
            )
        if self.stream_id is not None and not self.stream_id.strip():
            raise DatasetFormatError("stream_id cannot be blank")
        for channel_name, samples in (("accel", self.accel), ("gyro", self.gyro)):
            for index, sample in enumerate(samples):
                if len(sample) != 3 or not all(math.isfinite(value) for value in sample):
                    raise DatasetFormatError(
                        f"{channel_name} sample {index} must contain three finite values"
                    )

    @property
    def canonical_label(self) -> ActivityLabel:
        """Map source metadata through the shared canonical label table."""

        return map_activity_label(self.source_label)

    @property
    def stride(self) -> int:
        """Number of new samples introduced since the prior window in this stream."""

        return self.stride_samples if self.stride_samples is not None else len(self.accel)


class DatasetLoader(Protocol):
    """Re-iterable source of validated windows (needed by replay looping)."""

    def __iter__(self) -> Iterator[DatasetWindow]: ...


def require_directory(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_dir():
        raise DatasetError(f"dataset directory does not exist: {resolved}")
    return resolved


def parse_vector_row(text: str, *, path: Path, line_number: int) -> tuple[float, ...]:
    """Parse one whitespace-separated numeric row with a useful source error."""

    try:
        values = tuple(float(value) for value in text.split())
    except ValueError as exc:
        raise DatasetFormatError(f"{path}:{line_number}: expected numeric values") from exc
    if not values or not all(math.isfinite(value) for value in values):
        raise DatasetFormatError(f"{path}:{line_number}: expected finite numeric values")
    return values
