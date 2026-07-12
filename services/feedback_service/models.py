"""Private validation models and public API response shapes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from shared.schemas import Feedback

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FeedbackContent(BaseModel):
    """Strict LLM output, validated before it reaches a wire contract."""

    headline: Text = Field(max_length=100)
    detail: Text = Field(max_length=2000)
    severity: Literal["info", "warning", "critical"]
    recommendations: list[Text] = Field(min_length=1, max_length=5)
    disclaimer: Text = Field(max_length=500)

    @field_validator("recommendations")
    @classmethod
    def recommendations_are_unique(cls, value: list[str]) -> list[str]:
        if len({item.casefold() for item in value}) != len(value):
            raise ValueError("recommendations must be unique")
        return value

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class GenerateRequest(BaseModel):
    mode: Literal["feedback", "summary"] = "feedback"
    period: Literal["1h", "24h", "7d", "30d"] | None = None
    from_ts: datetime | None = Field(default=None, alias="from")
    to_ts: datetime | None = Field(default=None, alias="to")
    request_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("from_ts", "to_ts")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
            raise ValueError("timestamps must be timezone-aware UTC")
        return value

    @model_validator(mode="after")
    def ordered_range(self) -> GenerateRequest:
        if self.from_ts is not None and self.to_ts is not None and self.from_ts > self.to_ts:
            raise ValueError("from must not be after to")
        if self.request_id is not None:
            self.request_id = self.request_id.strip()
            if not self.request_id:
                raise ValueError("request_id cannot be blank")
        if self.period is not None and (self.from_ts is not None or self.to_ts is not None):
            raise ValueError("use either period or from/to, not both")
        return self

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class GenerationResponse(Feedback):
    """Direct dashboard payload plus transparent provider/fallback metadata."""

    fallback: bool = False
    provider_status: Literal["ok", "fallback", "empty"] = "ok"
    idempotent_replay: bool = False
