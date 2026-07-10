"""Numerically safe statistical features for six-axis IMU windows."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TypeAlias

from .windowing import SensorFrame, Vector3

FeatureMap: TypeAlias = dict[str, float]


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _std(values: Sequence[float], mean: float) -> float:
    return math.sqrt(math.fsum((value - mean) ** 2 for value in values) / len(values))


def _correlation(left: Sequence[float], right: Sequence[float]) -> float:
    left_mean, right_mean = _mean(left), _mean(right)
    left_ss = math.fsum((value - left_mean) ** 2 for value in left)
    right_ss = math.fsum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_ss * right_ss)
    if denominator <= 1e-12:
        return 0.0
    value = (
        math.fsum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
        / denominator
    )
    return max(-1.0, min(1.0, value))


def _add_summary(features: FeatureMap, name: str, values: Sequence[float]) -> None:
    mean = _mean(values)
    features[f"{name}_mean"] = mean
    features[f"{name}_std"] = _std(values, mean)
    features[f"{name}_min"] = min(values)
    features[f"{name}_max"] = max(values)
    features[f"{name}_energy"] = _mean([value * value for value in values])


def _magnitude(samples: Sequence[Vector3]) -> list[float]:
    return [math.sqrt(x * x + y * y + z * z) for x, y, z in samples]


def extract_features(frame: SensorFrame) -> FeatureMap:
    """Calculate all Milestone 2 features without optional numeric dependencies."""

    if not frame.samples:
        raise ValueError("cannot extract features from an empty frame")
    features: FeatureMap = {}
    channels: dict[str, list[float]] = {}
    for sensor_name, vectors in (("accel", frame.accel), ("gyro", frame.gyro)):
        for axis_index, axis_name in enumerate("xyz"):
            values = [sample[axis_index] for sample in vectors]
            channels[f"{sensor_name}_{axis_name}"] = values
            _add_summary(features, f"{sensor_name}_{axis_name}", values)

        magnitude = _magnitude(vectors)
        channels[f"{sensor_name}_magnitude"] = magnitude
        _add_summary(features, f"{sensor_name}_magnitude", magnitude)
        features[f"{sensor_name}_sma"] = _mean([abs(x) + abs(y) + abs(z) for x, y, z in vectors])
        for first, second in (("x", "y"), ("x", "z"), ("y", "z")):
            features[f"{sensor_name}_corr_{first}{second}"] = _correlation(
                channels[f"{sensor_name}_{first}"], channels[f"{sensor_name}_{second}"]
            )

    ax = features["accel_x_mean"]
    ay = features["accel_y_mean"]
    az = features["accel_z_mean"]
    features["tilt_x_degrees"] = math.degrees(math.atan2(ax, math.hypot(ay, az)))
    features["tilt_y_degrees"] = math.degrees(math.atan2(ay, math.hypot(ax, az)))
    features["tilt_z_degrees"] = math.degrees(math.atan2(az, math.hypot(ax, ay)))

    if not all(math.isfinite(value) for value in features.values()):
        raise ValueError("feature calculation produced a non-finite value")
    return features


def motion_intensity(frame: SensorFrame) -> float:
    """Return a bounded dynamic-acceleration score; calm gravity scores near zero."""

    magnitudes = _magnitude(frame.accel)
    baseline = sorted(magnitudes)[len(magnitudes) // 2]
    peak_deviation = max(abs(value - baseline) for value in magnitudes)
    # A 2g deviation saturates the fall/motion signal while ordinary noise remains low.
    return max(0.0, min(1.0, peak_deviation / 19.6133))
