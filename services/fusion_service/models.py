"""REST response contracts owned by the Fusion service."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from shared.labels import ActivityLabel, EventSeverity, EventType
from shared.schemas import Confidence


class ModalityStatus(BaseModel):
    status: Literal["online", "offline"]
    last_update: datetime | None = None


class ComponentStatus(BaseModel):
    status: Literal["healthy", "degraded"]
    detail: str | None = None


class FusionStatusResponse(BaseModel):
    activity: ActivityLabel = ActivityLabel.UNKNOWN
    confidence: Confidence = 0.0
    last_update: datetime | None = None
    data_status: Literal["current", "stale", "unavailable"] = "unavailable"
    modality_health: dict[Literal["sensor", "video"], ModalityStatus]
    components: dict[str, ComponentStatus] = Field(default_factory=dict)


class ActivityRecord(BaseModel):
    id: int
    ts: datetime
    activity: ActivityLabel
    confidence: Confidence
    sensor_label: ActivityLabel | None = None
    video_label: ActivityLabel | None = None
    duration_seconds: float = Field(default=0.0, ge=0.0)


class EventRecord(BaseModel):
    id: int
    ts: datetime
    type: EventType
    severity: EventSeverity
    confidence: Confidence
    evidence: dict[str, object]
    acknowledged: bool


class TimelineResponse(BaseModel):
    items: list[ActivityRecord]
    count: int


class EventsResponse(BaseModel):
    items: list[EventRecord]
    count: int


class TrendBucket(BaseModel):
    activity: ActivityLabel
    count: int = Field(ge=0)
    duration_seconds: float = Field(ge=0.0)


class TrendsResponse(BaseModel):
    period: str
    from_ts: datetime = Field(alias="from")
    to_ts: datetime = Field(alias="to")
    activities: list[TrendBucket]
    total_duration_seconds: float = Field(ge=0.0)

    model_config = {"populate_by_name": True}
