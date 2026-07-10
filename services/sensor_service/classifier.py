"""Isolated pre-trained inference adapter and deterministic safe fallback.

The pinned ST IGN artifact is licensed under SLA0044 and accepts FLOAT32
accelerometer windows shaped ``(1, window_length, 3, 1)``. Its model card calls
for gravity rotation/suppression preprocessing. This service never downloads a
model at runtime; deployments must supply a reviewed local runner that performs
those model-specific details. Tests inject that runner, keeping TensorFlow and
``huggingface_hub`` optional.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from shared.labels import ActivityLabel, map_activity_label

from .config import MODEL_LICENSE, SensorSettings
from .features import FeatureMap
from .windowing import GRAVITY_M_S2, SensorFrame

ModelOutput: TypeAlias = tuple[object, float] | Mapping[object, float]


class ModelRunner(Protocol):
    def __call__(
        self, accel_window: Sequence[tuple[float, float, float]], features: FeatureMap
    ) -> ModelOutput: ...


@dataclass(frozen=True)
class Classification:
    label: ActivityLabel
    confidence: float


class ModelUnavailable(RuntimeError):
    pass


class PretrainedModelAdapter:
    """Boundary around model-specific preprocessing and output conventions."""

    license = MODEL_LICENSE
    input_assumptions = (
        "SI acceleration input; converted to g, window-mean gravity suppressed, then "
        "standardized by configured mean/std"
    )

    def __init__(
        self,
        settings: SensorSettings,
        runner: ModelRunner | None = None,
        loader: Callable[[str, str], ModelRunner] | None = None,
    ) -> None:
        self.settings = settings
        self._runner = runner
        self._loader = loader
        self.failure_detail: str | None = None

    @property
    def available(self) -> bool:
        return self._runner is not None

    def load(self) -> None:
        """Load only via an injected/local deployment loader; never access the network."""

        if self._runner is not None:
            return
        if self._loader is None and self.settings.sensor_model_path is not None:
            try:
                from .local_model import load_local_tflite

                self._runner = load_local_tflite(
                    self.settings.sensor_model_path, self.settings.model_labels
                )
                return
            except Exception as exc:
                self.failure_detail = f"local model load failed ({type(exc).__name__})"
                raise ModelUnavailable(self.failure_detail) from exc
        if self._loader is None:
            self.failure_detail = "local model runner is not provisioned"
            raise ModelUnavailable(self.failure_detail)
        try:
            self._runner = self._loader(
                self.settings.sensor_model_id, self.settings.sensor_model_revision
            )
        except Exception as exc:
            self.failure_detail = f"local model load failed ({type(exc).__name__})"
            raise ModelUnavailable(self.failure_detail) from exc

    def predict(self, frame: SensorFrame, features: FeatureMap) -> Classification:
        if self._runner is None:
            raise ModelUnavailable(self.failure_detail or "model is unavailable")
        acceleration_g = [tuple(axis / GRAVITY_M_S2 for axis in sample) for sample in frame.accel]
        gravity = (
            tuple(
                sum(sample[axis] for sample in acceleration_g) / len(acceleration_g)
                for axis in range(3)
            )
            if self.settings.model_suppress_gravity
            else (0.0, 0.0, 0.0)
        )
        standardized = [
            tuple(
                ((axis - gravity[axis_index]) - self.settings.model_input_mean)
                / self.settings.model_input_std
                for axis_index, axis in enumerate(sample)
            )
            for sample in acceleration_g
        ]
        try:
            output = self._runner(standardized, features)
            label, confidence = _best_output(output)
        except Exception as exc:
            self.failure_detail = f"model inference failed ({type(exc).__name__})"
            raise ModelUnavailable(self.failure_detail) from exc
        canonical_label = map_activity_label(label)
        canonical_confidence = (
            0.0 if canonical_label is ActivityLabel.UNKNOWN else _confidence(confidence)
        )
        return Classification(canonical_label, canonical_confidence)


def _best_output(output: ModelOutput) -> tuple[object, float]:
    if isinstance(output, Mapping):
        if not output:
            return ActivityLabel.UNKNOWN, 0.0
        label, confidence = max(output.items(), key=lambda item: float(item[1]))
        return label, float(confidence)
    if not isinstance(output, tuple) or len(output) != 2:
        raise ValueError("model output must be (label, confidence) or class-score mapping")
    return output[0], float(output[1])


def _confidence(value: float) -> float:
    if value != value:  # NaN
        return 0.0
    return max(0.0, min(1.0, value))


class DeterministicFallback:
    """Conservative thresholds for continuity, not a replacement for the model."""

    def predict(self, frame: SensorFrame, features: FeatureMap, intensity: float) -> Classification:
        accel_std = sum(features[f"accel_{axis}_std"] for axis in "xyz") / 3.0
        gyro_energy = features["gyro_magnitude_energy"]
        mean_magnitude = features["accel_magnitude_mean"]

        if intensity >= 0.6 or gyro_energy >= 2.25:
            return Classification(ActivityLabel.EXERCISING, 0.82)
        if intensity >= 0.08 or accel_std >= 0.75:
            confidence = min(0.9, 0.58 + intensity)
            return Classification(ActivityLabel.WALKING, confidence)
        if mean_magnitude >= 6.0:
            # A horizontal device is only weak evidence of body posture, so keep
            # this heuristic deliberately below model-grade confidence.
            if abs(features["tilt_z_degrees"]) < 35.0:
                return Classification(ActivityLabel.LYING, 0.58)
            return Classification(ActivityLabel.STANDING, 0.66)
        if accel_std < 0.2:
            return Classification(ActivityLabel.SITTING, 0.55)
        return Classification(ActivityLabel.UNKNOWN, 0.2)
