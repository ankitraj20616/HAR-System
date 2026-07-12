"""Unit normalization and deterministic per-device sliding windows."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypeAlias

from shared.schemas import SensorRaw

from .config import SensorSettings

GRAVITY_M_S2 = 9.80665
Vector3: TypeAlias = tuple[float, float, float]


@dataclass(frozen=True)
class SensorSample:
    ts: datetime
    accel: Vector3
    gyro: Vector3


@dataclass(frozen=True)
class SensorFrame:
    device_id: str
    sampling_hz: float
    samples: tuple[SensorSample, ...]

    @property
    def ts(self) -> datetime:
        """Timestamp of the last sample, used for ordered predictions."""

        return self.samples[-1].ts

    @property
    def accel(self) -> tuple[Vector3, ...]:
        return tuple(sample.accel for sample in self.samples)

    @property
    def gyro(self) -> tuple[Vector3, ...]:
        return tuple(sample.gyro for sample in self.samples)


class StaleSensorPayload(ValueError):
    """Raised when an input would make a device's predictions go backwards."""


@dataclass
class _DeviceBuffer:
    sampling_hz: float
    samples: deque[SensorSample] = field(default_factory=deque)
    last_input_ts: datetime | None = None


def normalize_vector(
    vector: tuple[float, float, float], scale: float, unit_scale: float
) -> Vector3:
    normalized = tuple(float(value) * scale * unit_scale for value in vector)
    if len(normalized) != 3 or not all(math.isfinite(value) for value in normalized):
        raise ValueError("sensor vector must contain three finite values")
    return normalized  # type: ignore[return-value]


class SlidingWindowBuffer:
    """Convert payload chunks into overlapping, normalized fixed windows."""

    def __init__(self, settings: SensorSettings) -> None:
        self.settings = settings
        self._devices: dict[str, _DeviceBuffer] = {}

    def add(self, raw: SensorRaw) -> list[SensorFrame]:
        sampling_hz = float(raw.sampling_hz)
        state = self._devices.get(raw.device_id)
        if state is None or not math.isclose(state.sampling_hz, sampling_hz):
            state = _DeviceBuffer(sampling_hz=sampling_hz)
            self._devices[raw.device_id] = state
        if state.last_input_ts is not None and raw.ts <= state.last_input_ts:
            raise StaleSensorPayload("sensor payload timestamp is not newer than prior payload")

        accel_unit_scale = GRAVITY_M_S2 if self.settings.accel_unit == "g" else 1.0
        gyro_unit_scale = math.pi / 180.0 if self.settings.gyro_unit == "deg_s" else 1.0
        interval = 1.0 / sampling_hz
        sample_count = len(raw.window.accel)
        first_sample_ts = raw.ts - timedelta(seconds=(sample_count - 1) * interval)
        # A full first window after an overlapped stream/scenario boundary reaches
        # back before buffered samples. Reset instead of mixing or duplicating time.
        if state.samples and first_sample_ts <= state.samples[-1].ts:
            state.samples.clear()
        for index, (accel, gyro) in enumerate(zip(raw.window.accel, raw.window.gyro, strict=True)):
            state.samples.append(
                SensorSample(
                    ts=first_sample_ts + timedelta(seconds=index * interval),
                    accel=normalize_vector(accel, self.settings.accel_scale, accel_unit_scale),
                    gyro=normalize_vector(gyro, self.settings.gyro_scale, gyro_unit_scale),
                )
            )
        state.last_input_ts = raw.ts

        frames: list[SensorFrame] = []
        while len(state.samples) >= self.settings.window_size:
            samples = tuple(list(state.samples)[: self.settings.window_size])
            frames.append(
                SensorFrame(
                    device_id=raw.device_id,
                    sampling_hz=sampling_hz,
                    samples=samples,
                )
            )
            for _ in range(self.settings.window_step):
                state.samples.popleft()
        return frames

    def clear(self) -> None:
        self._devices.clear()
