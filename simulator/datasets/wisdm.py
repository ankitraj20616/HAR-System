"""Streaming loader for the WISDM raw accelerometer text format."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .base import DatasetError, DatasetFormatError, DatasetWindow


@dataclass(frozen=True, slots=True)
class WisdmLoader:
    """Window WISDM rows, normalize m/s² to g, and supply zero gyro."""

    path: str | Path
    sampling_hz: float = 20.0
    window_size: int = 128
    window_stride: int = 64
    base_timestamp: datetime = datetime(2020, 1, 1, tzinfo=UTC)
    strict: bool = True
    standard_gravity: float = 9.80665

    def __post_init__(self) -> None:
        if self.window_size <= 0 or not 0 < self.window_stride <= self.window_size:
            raise ValueError("window_size and window_stride must be positive and stride <= size")
        if not math.isfinite(self.sampling_hz) or self.sampling_hz <= 0:
            raise ValueError("sampling_hz must be positive and finite")
        if not math.isfinite(self.standard_gravity) or self.standard_gravity <= 0:
            raise ValueError("standard_gravity must be positive and finite")
        if self.base_timestamp.tzinfo is None or self.base_timestamp.utcoffset() != timedelta(0):
            raise ValueError("base_timestamp must use UTC")

    def __iter__(self):
        path = Path(self.path).expanduser()
        if path.is_dir():
            candidates = sorted(path.glob("*.txt")) + sorted(path.glob("*.csv"))
            if not candidates:
                raise DatasetError(f"no WISDM .txt or .csv file found in {path}")
            path = candidates[0]
        if not path.is_file():
            raise DatasetError(f"WISDM file does not exist: {path}")

        current_key: tuple[str, str] | None = None
        segment = 0
        window_number = 0
        buffer: list[tuple[float, float, float]] = []
        with path.open(encoding="utf-8") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                line = raw_line.strip().rstrip(";")
                if not line:
                    continue
                try:
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) != 6:
                        raise ValueError
                    user, label, _source_timestamp = parts[:3]
                    sample = tuple(float(value) for value in parts[3:6])
                    if not user or not label or not all(math.isfinite(value) for value in sample):
                        raise ValueError
                except ValueError as exc:
                    if self.strict:
                        raise DatasetFormatError(
                            f"{path}:{line_number}: expected user,label,timestamp,x,y,z"
                        ) from exc
                    continue

                key = (user, label)
                if key != current_key:
                    current_key = key
                    segment += 1
                    buffer.clear()
                buffer.append(tuple(value / self.standard_gravity for value in sample))  # type: ignore[arg-type]
                if len(buffer) < self.window_size:
                    continue
                timestamp = self.base_timestamp + timedelta(
                    seconds=window_number * self.window_stride / self.sampling_hz
                )
                yield DatasetWindow(
                    timestamp=timestamp,
                    sampling_hz=self.sampling_hz,
                    accel=tuple(buffer),
                    gyro=((0.0, 0.0, 0.0),) * self.window_size,
                    source_label=label,
                    scenario_id=f"wisdm-user-{user}-segment-{segment:04d}",
                    stride_samples=self.window_stride,
                    stream_id=f"wisdm-user-{user}-segment-{segment:04d}",
                )
                window_number += 1
                del buffer[: self.window_stride]
