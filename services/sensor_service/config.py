"""Validated, environment-driven configuration for sensor recognition."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from shared.config import Settings

SERVICE_NAME = "sensor_service"
SERVICE_TITLE = "HAR Sensor Service"

# The revision is deliberately immutable. Runtime loading is local-only: deployment
# must provision the artifact and accept its license before starting the service.
DEFAULT_MODEL_ID = "STMicroelectronics/IGN-HAR-model"
DEFAULT_MODEL_REVISION = "69f07d89b9520c9ab4424fafed6d079c3d12b26d"
MODEL_LICENSE = "SLA0044 (review required before redistribution/commercial use)"


class SensorSettings(Settings):
    """Sensor-specific settings layered over the common service settings."""

    window_size: int = Field(default=128, ge=20, le=4096)
    window_overlap: float = Field(default=0.5, ge=0.0, lt=1.0, allow_inf_nan=False)
    sensor_model_id: str = DEFAULT_MODEL_ID
    sensor_model_revision: str = DEFAULT_MODEL_REVISION
    sensor_model_path: Path | None = None
    # JSON-free comma-separated class order, e.g. UNKNOWN,WALKING,EXERCISING,WALKING.
    # It is intentionally required whenever a local artifact is configured: class
    # order is a property of the exact artifact and must never be guessed.
    sensor_model_labels: str = ""
    use_fallback: bool = False

    accel_unit: Literal["g", "m_s2"] = "g"
    gyro_unit: Literal["deg_s", "rad_s"] = "rad_s"
    accel_scale: float = Field(default=1.0, gt=0.0, allow_inf_nan=False)
    gyro_scale: float = Field(default=1.0, gt=0.0, allow_inf_nan=False)
    model_input_mean: float = Field(default=0.0, allow_inf_nan=False)
    model_input_std: float = Field(default=1.0, gt=0.0, allow_inf_nan=False)
    model_suppress_gravity: bool = True

    @field_validator("sensor_model_id", "sensor_model_revision")
    @classmethod
    def non_empty_model_reference(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model ID and revision cannot be empty")
        return value

    @field_validator("sensor_model_path", mode="before")
    @classmethod
    def blank_model_path_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def window_step_must_be_positive(self) -> "SensorSettings":
        if round(self.window_size * (1.0 - self.window_overlap)) < 1:
            raise ValueError("WINDOW_OVERLAP leaves no samples between windows")
        if self.sensor_model_path is not None and not self.model_labels:
            raise ValueError("SENSOR_MODEL_LABELS is required with SENSOR_MODEL_PATH")
        return self

    @property
    def window_step(self) -> int:
        """Integer number of new samples needed for the next window."""

        return max(1, round(self.window_size * (1.0 - self.window_overlap)))

    @property
    def model_labels(self) -> tuple[str, ...]:
        return tuple(
            label.strip() for label in self.sensor_model_labels.split(",") if label.strip()
        )


@lru_cache
def get_service_settings() -> SensorSettings:
    return SensorSettings()
