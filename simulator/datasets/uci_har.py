"""Loader for the standard UCI Human Activity Recognition dataset layout."""

from __future__ import annotations

import math
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import zip_longest
from pathlib import Path

from .base import (
    DatasetError,
    DatasetFormatError,
    DatasetWindow,
    parse_vector_row,
    require_directory,
)

_SIGNALS = (
    "total_acc_x",
    "total_acc_y",
    "total_acc_z",
    "body_gyro_x",
    "body_gyro_y",
    "body_gyro_z",
)


@dataclass(frozen=True, slots=True)
class UciHarLoader:
    """Yield UCI HAR train/test windows in deterministic file order."""

    path: str | Path
    sampling_hz: float = 50.0
    splits: tuple[str, ...] = ("train", "test")
    base_timestamp: datetime = datetime(2020, 1, 1, tzinfo=UTC)
    window_stride: int = 64

    def __post_init__(self) -> None:
        if not math.isfinite(self.sampling_hz) or self.sampling_hz <= 0 or self.window_stride <= 0:
            raise ValueError("sampling_hz and window_stride must be positive")
        if self.base_timestamp.tzinfo is None or self.base_timestamp.utcoffset() != timedelta(0):
            raise ValueError("base_timestamp must use UTC")

    def __iter__(self):
        root = self._root()
        labels = self._activity_labels(root)
        emitted = 0
        for split in self.splits:
            if split not in {"train", "test"}:
                raise DatasetError(f"unsupported UCI HAR split: {split!r}")
            split_dir = root / split
            signals_dir = split_dir / "Inertial Signals"
            label_path = split_dir / f"y_{split}.txt"
            subject_path = split_dir / f"subject_{split}.txt"
            paths = [signals_dir / f"{name}_{split}.txt" for name in _SIGNALS]
            required = [*paths, label_path, subject_path]
            missing = [str(path) for path in required if not path.is_file()]
            if missing:
                raise DatasetError("missing UCI HAR files: " + ", ".join(missing))

            with ExitStack() as stack:
                streams = [stack.enter_context(path.open(encoding="utf-8")) for path in paths]
                label_stream = stack.enter_context(label_path.open(encoding="utf-8"))
                subject_stream = stack.enter_context(subject_path.open(encoding="utf-8"))
                rows = zip_longest(*streams, label_stream, subject_stream)
                for row_number, row in enumerate(rows, start=1):
                    if any(value is None for value in row):
                        raise DatasetFormatError(
                            f"UCI HAR {split} files have different row counts near row {row_number}"
                        )
                    signal_rows = [
                        parse_vector_row(value, path=path, line_number=row_number)
                        for value, path in zip(row[:6], paths, strict=True)
                    ]
                    lengths = {len(values) for values in signal_rows}
                    if len(lengths) != 1:
                        raise DatasetFormatError(
                            f"UCI HAR {split} signal lengths differ at row {row_number}"
                        )
                    try:
                        label_id = int(row[6].strip())
                        subject_id = int(row[7].strip())
                    except ValueError as exc:
                        raise DatasetFormatError(
                            f"UCI HAR {split} has invalid metadata at row {row_number}"
                        ) from exc
                    source_label = labels.get(label_id, f"UNMAPPED_{label_id}")
                    accel = tuple(zip(*signal_rows[:3], strict=True))
                    gyro = tuple(zip(*signal_rows[3:], strict=True))
                    timestamp = self.base_timestamp + timedelta(
                        seconds=emitted * self.window_stride / self.sampling_hz
                    )
                    yield DatasetWindow(
                        timestamp=timestamp,
                        sampling_hz=self.sampling_hz,
                        accel=accel,
                        gyro=gyro,
                        source_label=source_label,
                        scenario_id=(
                            f"uci-{split}-subject-{subject_id:02d}-window-{row_number:06d}"
                        ),
                        stride_samples=self.window_stride,
                        stream_id=f"uci-{split}-subject-{subject_id:02d}",
                    )
                    emitted += 1

    def _root(self) -> Path:
        root = require_directory(self.path)
        nested = root / "UCI HAR Dataset"
        return nested if nested.is_dir() else root

    @staticmethod
    def _activity_labels(root: Path) -> dict[int, str]:
        path = root / "activity_labels.txt"
        if not path.is_file():
            raise DatasetError(f"missing UCI HAR activity labels: {path}")
        labels: dict[int, str] = {}
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise DatasetFormatError(f"{path}:{line_number}: invalid activity label")
            try:
                labels[int(parts[0])] = parts[1].strip()
            except ValueError as exc:
                raise DatasetFormatError(f"{path}:{line_number}: invalid activity id") from exc
        if not labels:
            raise DatasetFormatError(f"{path}: no activity labels found")
        return labels
