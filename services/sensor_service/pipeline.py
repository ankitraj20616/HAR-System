"""Contract-valid sensor payload to prediction orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from pydantic import ValidationError

from shared.labels import ActivityLabel, Modality
from shared.schemas import SensorPrediction, SensorRaw

from .classifier import (
    Classification,
    DeterministicFallback,
    ModelUnavailable,
    PretrainedModelAdapter,
)
from .config import SensorSettings
from .features import extract_features, motion_intensity
from .windowing import SlidingWindowBuffer


class InvalidSensorPayload(ValueError):
    """Safe wrapper that does not include raw input in its error string."""


@dataclass(frozen=True)
class PipelineHealth:
    degraded: bool
    detail: str


class SensorPipeline:
    def __init__(
        self,
        settings: SensorSettings,
        model: PretrainedModelAdapter | None = None,
        fallback: DeterministicFallback | None = None,
    ) -> None:
        self.settings = settings
        self.windowing = SlidingWindowBuffer(settings)
        self.model = model or PretrainedModelAdapter(settings)
        self.fallback = fallback or DeterministicFallback()
        self._lock = Lock()
        self._model_failure: str | None = None
        self._last_prediction_ts: dict[str, datetime] = {}

    def start(self) -> None:
        try:
            self.model.load()
            self._model_failure = None
        except ModelUnavailable as exc:
            self._model_failure = str(exc)

    @property
    def health(self) -> PipelineHealth:
        if self._model_failure:
            mode = "fallback active" if self.settings.use_fallback else "UNKNOWN safety mode"
            return PipelineHealth(True, f"{self._model_failure}; {mode}")
        return PipelineHealth(False, "pinned model ready")

    def process_json(self, payload: bytes | str) -> list[SensorPrediction]:
        try:
            raw = SensorRaw.model_validate_json(payload)
        except (ValidationError, ValueError, TypeError) as exc:
            raise InvalidSensorPayload(
                f"raw sensor contract rejected ({type(exc).__name__})"
            ) from exc
        return self.process(raw)

    def process(self, raw: SensorRaw) -> list[SensorPrediction]:
        with self._lock:
            predictions: list[SensorPrediction] = []
            for frame in self.windowing.add(raw):
                features = extract_features(frame)
                intensity = motion_intensity(frame)
                classification = self._classify(frame, features, intensity)
                last_ts = self._last_prediction_ts.get(frame.device_id)
                if last_ts is not None and frame.ts <= last_ts:
                    continue
                prediction = SensorPrediction(
                    ts=frame.ts,
                    modality=Modality.SENSOR,
                    label=classification.label,
                    confidence=classification.confidence,
                    motion_intensity=intensity,
                )
                self._last_prediction_ts[frame.device_id] = prediction.ts
                predictions.append(prediction)
            return predictions

    def _classify(self, frame, features, intensity: float) -> Classification:
        try:
            result = self.model.predict(frame, features)
            self._model_failure = None
            return result
        except ModelUnavailable as exc:
            self._model_failure = str(exc)
            if self.settings.use_fallback:
                return self.fallback.predict(frame, features, intensity)
            return Classification(ActivityLabel.UNKNOWN, 0.0)
