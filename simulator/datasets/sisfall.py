"""Loader for SisFall scenario files."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .base import DatasetError, DatasetFormatError, DatasetWindow, require_directory

# Conservative source-to-project mapping. Fall remains evaluation metadata and
# intentionally maps to UNKNOWN as it is an event, not an ActivityLabel.
_DAILY_ACTIVITY_LABELS = {
    "D01": "WALKING",
    "D02": "WALKING",
    "D03": "EXERCISING",
    "D04": "EXERCISING",
    "D05": "WALKING_UPSTAIRS",
    "D06": "WALKING_DOWNSTAIRS",
    "D07": "SITTING",
    "D08": "SITTING",
    "D09": "SITTING",
    "D10": "SITTING",
    "D11": "SITTING",
    "D12": "SITTING",
    "D13": "SITTING",
    "D14": "LYING",
    "D15": "STANDING",
    "D16": "STANDING",
    "D18": "WALKING",
    "D19": "EXERCISING",
}


@dataclass(frozen=True, slots=True)
class SisFallLoader:
    """Yield SI-compatible windows from sorted SisFall ``Dxx/Fxx`` files."""

    path: str | Path
    sampling_hz: float = 200.0
    window_size: int = 128
    window_stride: int = 64
    base_timestamp: datetime = datetime(2020, 1, 1, tzinfo=UTC)
    strict: bool = True
    accel_lsb_per_g: float = 256.0
    gyro_lsb_per_degree_second: float = 14.375

    def __post_init__(self) -> None:
        if self.window_size <= 0 or not 0 < self.window_stride <= self.window_size:
            raise ValueError("window_size and window_stride must be positive and stride <= size")
        if not math.isfinite(self.sampling_hz) or self.sampling_hz <= 0:
            raise ValueError("sampling_hz must be positive and finite")
        if self.accel_lsb_per_g <= 0 or self.gyro_lsb_per_degree_second <= 0:
            raise ValueError("SisFall sensor scale factors must be positive")
        if self.base_timestamp.tzinfo is None or self.base_timestamp.utcoffset() != timedelta(0):
            raise ValueError("base_timestamp must use UTC")

    def __iter__(self):
        root = require_directory(self.path)
        paths = sorted(
            path
            for path in (*root.rglob("*.txt"), *root.rglob("*.csv"))
            if path.stem.upper().startswith(("D", "F")) and "_" in path.stem
        )
        if not paths:
            raise DatasetError(f"no SisFall scenario files found in {root}")
        emitted = 0
        for path in paths:
            scenario_id = path.stem
            code = scenario_id.split("_", maxsplit=1)[0].upper()
            if code.startswith("F"):
                source_label = "FALL"
            else:
                source_label = _DAILY_ACTIVITY_LABELS.get(code, code)
            samples: list[tuple[float, ...]] = []
            with path.open(encoding="utf-8") as stream:
                for line_number, raw_line in enumerate(stream, start=1):
                    line = raw_line.strip().rstrip(";")
                    if not line:
                        continue
                    try:
                        fields = line.replace(";", ",").split(",")
                        values = tuple(float(value.strip()) for value in fields)
                        if len(values) < 6 or not all(math.isfinite(value) for value in values):
                            raise ValueError
                    except ValueError as exc:
                        if self.strict:
                            raise DatasetFormatError(
                                f"{path}:{line_number}: expected at least six finite sensor values"
                            ) from exc
                        continue
                    samples.append(values)
            for start in range(0, len(samples) - self.window_size + 1, self.window_stride):
                window = samples[start : start + self.window_size]
                timestamp = self.base_timestamp + timedelta(
                    seconds=emitted * self.window_stride / self.sampling_hz
                )
                yield DatasetWindow(
                    timestamp=timestamp,
                    sampling_hz=self.sampling_hz,
                    # ADXL345 raw counts -> g. The sensor service's default
                    # ACCEL_UNIT=g performs the final conversion to m/s².
                    accel=tuple(
                        tuple(value / self.accel_lsb_per_g for value in row[:3]) for row in window
                    ),  # type: ignore[arg-type]
                    # ITG3200 raw counts -> rad/s, matching GYRO_UNIT=rad_s.
                    gyro=tuple(
                        tuple(
                            math.radians(value / self.gyro_lsb_per_degree_second)
                            for value in row[3:6]
                        )
                        for row in window
                    ),  # type: ignore[arg-type]
                    source_label=source_label,
                    scenario_id=scenario_id,
                    stride_samples=self.window_stride,
                    stream_id=scenario_id,
                )
                emitted += 1
