"""Validated, environment-driven configuration for the Fusion service."""

from __future__ import annotations

import json
import math
from datetime import timedelta
from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import NoDecode

from shared.config import Settings

SERVICE_NAME = "fusion_service"
SERVICE_TITLE = "HAR Fusion Service"


class FusionSettings(Settings):
    """Fusion, safety, API, and queue limits controlled by environment variables."""

    # ``NoDecode`` lets us support the documented sensor=0.5,video=0.5 syntax.
    modality_weights: Annotated[dict[str, float], NoDecode] = Field(
        default_factory=lambda: {"sensor": 0.5, "video": 0.5}
    )
    smoothing_window: int = Field(default=5, ge=1, le=1001)
    fusion_interval: float = Field(default=1.0, gt=0.0, le=60.0, allow_inf_nan=False)
    alignment_tolerance_ms: int = Field(default=1300, ge=0, le=60_000)
    buffer_retention_ms: int = Field(default=10_000, gt=0, le=3_600_000)
    buffer_max_size: int = Field(default=256, ge=1, le=100_000)
    stale_timeout_seconds: float = Field(default=3.0, gt=0.0, le=3600.0, allow_inf_nan=False)

    fall_accel_threshold: float = Field(default=2.5, gt=0.0, allow_inf_nan=False)
    fall_correlation_ms: int = Field(default=1500, gt=0, le=60_000)
    fall_cooldown_seconds: float = Field(default=30.0, ge=0.0, le=86_400.0, allow_inf_nan=False)
    fall_recovery_timeout_seconds: float = Field(
        default=60.0, gt=0.0, le=86_400.0, allow_inf_nan=False
    )
    inactivity_seconds: float = Field(default=1800.0, gt=0.0, le=2_592_000.0, allow_inf_nan=False)
    inactivity_motion_threshold: float = Field(default=0.08, ge=0.0, allow_inf_nan=False)
    abnormal_min_seconds: float = Field(default=3600.0, gt=0.0, le=2_592_000.0, allow_inf_nan=False)
    abnormal_baseline_samples: int = Field(default=5, ge=2, le=100_000)
    abnormal_baseline_multiplier: float = Field(default=3.0, gt=1.0, allow_inf_nan=False)

    websocket_queue_size: int = Field(default=64, ge=1, le=100_000)
    input_queue_size: int = Field(default=512, ge=1, le=1_000_000)
    api_max_limit: int = Field(default=1000, ge=1, le=1000)

    @field_validator("modality_weights", mode="before")
    @classmethod
    def parse_modality_weights(cls, value: Any) -> dict[str, float]:
        """Parse either a mapping or the documented comma-separated syntax."""

        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("MODALITY_WEIGHTS cannot be empty")
            if text.startswith("{"):
                try:
                    value = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError("MODALITY_WEIGHTS contains invalid JSON") from exc
            else:
                parsed: dict[str, float] = {}
                for item in text.split(","):
                    if item.count("=") != 1:
                        raise ValueError("MODALITY_WEIGHTS must use sensor=<weight>,video=<weight>")
                    name, raw_weight = (part.strip() for part in item.split("=", 1))
                    if not name or not raw_weight:
                        raise ValueError("MODALITY_WEIGHTS names and values cannot be empty")
                    if name in parsed:
                        raise ValueError(f"duplicate modality weight {name!r}")
                    try:
                        parsed[name] = float(raw_weight)
                    except ValueError as exc:
                        raise ValueError(f"invalid weight for modality {name!r}") from exc
                value = parsed

        if not isinstance(value, dict):
            raise ValueError("MODALITY_WEIGHTS must be a mapping")

        normalized: dict[str, float] = {}
        for raw_name, raw_weight in value.items():
            if not isinstance(raw_name, str):
                raise ValueError("modality weight names must be strings")
            name = raw_name.strip().lower()
            if name in normalized:
                raise ValueError(f"duplicate modality weight {name!r}")
            if isinstance(raw_weight, bool):
                raise ValueError(f"invalid weight for modality {name!r}")
            try:
                weight = float(raw_weight)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid weight for modality {name!r}") from exc
            if not math.isfinite(weight) or weight <= 0.0:
                raise ValueError(f"weight for modality {name!r} must be finite and positive")
            normalized[name] = weight
        return normalized

    @model_validator(mode="after")
    def coherent_fusion_settings(self) -> FusionSettings:
        expected_modalities = {"sensor", "video"}
        if set(self.modality_weights) != expected_modalities:
            raise ValueError("MODALITY_WEIGHTS must contain exactly sensor and video")
        if self.buffer_retention_ms < self.alignment_tolerance_ms:
            raise ValueError("BUFFER_RETENTION_MS must cover ALIGNMENT_TOLERANCE_MS")
        if self.stale_timeout_seconds * 1000 < self.alignment_tolerance_ms:
            raise ValueError("STALE_TIMEOUT_SECONDS must cover ALIGNMENT_TOLERANCE_MS")
        return self

    @property
    def normalized_modality_weights(self) -> dict[str, float]:
        total = sum(self.modality_weights.values())
        return {name: weight / total for name, weight in self.modality_weights.items()}

    @property
    def alignment_tolerance(self) -> timedelta:
        return timedelta(milliseconds=self.alignment_tolerance_ms)

    @property
    def buffer_retention(self) -> timedelta:
        return timedelta(milliseconds=self.buffer_retention_ms)

    @property
    def stale_timeout(self) -> timedelta:
        return timedelta(seconds=self.stale_timeout_seconds)


@lru_cache(maxsize=1)
def get_service_settings() -> FusionSettings:
    return FusionSettings()
