"""Versioned Pydantic message contracts shared by all services."""

import json
from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    confloat,
    constr,
    field_validator,
    model_validator,
)

from .labels import (
    ActivityLabel,
    EventSeverity,
    EventType,
    FeedbackMode,
    Modality,
    Orientation,
)

MESSAGE_SCHEMA_VERSION = "1.0"
Confidence = confloat(ge=0.0, le=1.0, allow_inf_nan=False)
FiniteFloat = confloat(allow_inf_nan=False)
Vector3 = tuple[FiniteFloat, FiniteFloat, FiniteFloat]
NonEmptyText = constr(strip_whitespace=True, min_length=1)


class ContractModel(BaseModel):
    """Strict base for JSON messages.

    Version 1 allows new optional fields but never changes or removes existing
    fields. A breaking change must use a new major ``schema_version``.
    """

    schema_version: str = Field(default=MESSAGE_SCHEMA_VERSION)

    @field_validator("schema_version")
    @classmethod
    def known_schema_version(cls, value: str) -> str:
        if value != MESSAGE_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version {value!r}")
        return value

    model_config = ConfigDict(
        extra="forbid",
        hide_input_in_errors=True,
        use_enum_values=True,
        validate_assignment=True,
    )


class TimestampedContract(ContractModel):
    ts: datetime

    @field_validator("ts", mode="before")
    @classmethod
    def timestamp_must_use_iso_datetime(cls, value: Any) -> Any:
        # Pydantic otherwise accepts Unix epoch numbers for a datetime field,
        # but the MQTT wire contract explicitly requires ISO-8601 timestamps.
        if isinstance(value, bool) or not isinstance(value, str | datetime):
            raise ValueError("timestamp must be an ISO-8601 datetime")
        if isinstance(value, str) and not value.strip():
            raise ValueError("timestamp must be an ISO-8601 datetime")
        return value

    @field_validator("ts")
    @classmethod
    def timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware UTC")
        if value.utcoffset() != timedelta(0):
            raise ValueError("timestamp must use UTC (Z or +00:00)")
        return value


class SensorWindow(BaseModel):
    accel: list[Vector3] = Field(..., min_length=1)
    gyro: list[Vector3] = Field(..., min_length=1)

    @model_validator(mode="after")
    def matching_non_empty_channels(self) -> "SensorWindow":
        if len(self.accel) != len(self.gyro):
            raise ValueError("accel and gyro must contain the same number of samples")
        return self

    # Validation failures may be logged by MQTT consumers; hiding the input
    # prevents an entire raw sensor window from leaking into structured logs.
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class SensorRaw(TimestampedContract):
    device_id: NonEmptyText
    sampling_hz: confloat(gt=0.0, le=1000.0, allow_inf_nan=False)
    window: SensorWindow


class SensorPrediction(TimestampedContract):
    modality: Modality
    label: ActivityLabel
    confidence: Confidence
    motion_intensity: confloat(ge=0.0, allow_inf_nan=False)

    @field_validator("modality")
    @classmethod
    def sensor_modality_only(cls, value: str) -> str:
        if value != Modality.SENSOR:
            raise ValueError("sensor prediction modality must be 'sensor'")
        return value


class VideoPrediction(TimestampedContract):
    modality: Modality
    label: ActivityLabel
    confidence: Confidence
    orientation: Orientation

    @field_validator("modality")
    @classmethod
    def video_modality_only(cls, value: str) -> str:
        if value != Modality.VIDEO:
            raise ValueError("video prediction modality must be 'video'")
        return value


class Contributors(BaseModel):
    sensor: ActivityLabel | None = None
    video: ActivityLabel | None = None

    @model_validator(mode="after")
    def at_least_one_contributor(self) -> "Contributors":
        if self.sensor is None and self.video is None:
            raise ValueError("at least one modality must contribute")
        return self

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, use_enum_values=True)


class FusedActivity(TimestampedContract):
    activity: ActivityLabel
    confidence: Confidence
    contributors: Contributors


JsonValue = Any


class HAREvent(TimestampedContract):
    type: EventType
    severity: EventSeverity
    confidence: Confidence
    evidence: dict[str, JsonValue]

    @field_validator("evidence")
    @classmethod
    def evidence_must_be_json_safe(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("evidence must contain JSON-compatible values") from exc
        return value


class Feedback(TimestampedContract):
    mode: FeedbackMode
    headline: NonEmptyText
    detail: NonEmptyText
    severity: EventSeverity
    recommendations: list[NonEmptyText]
    disclaimer: NonEmptyText

    @field_validator("recommendations")
    @classmethod
    def recommendations_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("recommendations must not contain duplicates")
        return value


EnvelopeData = FusedActivity | HAREvent | Feedback


class WebSocketEnvelope(ContractModel):
    """A typed dashboard message whose channel must match its payload."""

    channel: Literal["activity", "event", "feedback"]
    data: EnvelopeData

    @model_validator(mode="after")
    def channel_must_match_payload(self) -> "WebSocketEnvelope":
        expected_type = {
            "activity": FusedActivity,
            "event": HAREvent,
            "feedback": Feedback,
        }[self.channel]
        if not isinstance(self.data, expected_type):
            raise ValueError(f"{self.channel!r} channel has the wrong payload type")
        return self
