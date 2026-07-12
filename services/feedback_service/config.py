"""Validated settings for structured, safety-checked feedback generation."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator

from shared.config import Settings

SERVICE_NAME = "feedback_service"
SERVICE_TITLE = "HAR Feedback Service"


class FeedbackSettings(Settings):
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:3b"
    ollama_host: str = "http://localhost:11434"
    generation_timeout: float = Field(default=30.0, gt=0, le=300)
    feedback_interval: int = Field(default=900, ge=10, le=86_400)
    summary_schedule: str = "0 0 * * *"
    maximum_digest_size: int = Field(default=12_000, ge=512, le=100_000)
    feedback_fallback_enabled: bool = True
    feedback_max_recommendations: int = Field(default=5, ge=1, le=10)
    feedback_default_period_hours: int = Field(default=24, ge=1, le=24 * 30)
    feedback_api_max_period_days: int = Field(default=30, ge=1, le=365)
    feedback_input_queue_size: int = Field(default=128, ge=1, le=10_000)
    feedback_websocket_queue_size: int = Field(default=64, ge=1, le=10_000)

    @field_validator("llm_provider")
    @classmethod
    def provider_is_supported(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "ollama":
            raise ValueError("LLM_PROVIDER currently supports the offline 'ollama' adapter")
        return normalized

    @field_validator("llm_model", "ollama_host")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("setting cannot be empty")
        return value.rstrip("/") if value.startswith(("http://", "https://")) else value

    @field_validator("summary_schedule")
    @classmethod
    def daily_summary_schedule(cls, value: str) -> str:
        parts = value.strip().split()
        if len(parts) != 5 or parts[2:] != ["*", "*", "*"]:
            raise ValueError("SUMMARY_SCHEDULE must be a daily cron expression: minute hour * * *")
        try:
            minute, hour = (int(parts[0]), int(parts[1]))
        except ValueError as exc:
            raise ValueError("SUMMARY_SCHEDULE minute and hour must be integers") from exc
        if not 0 <= minute <= 59 or not 0 <= hour <= 23:
            raise ValueError("SUMMARY_SCHEDULE contains an invalid UTC time")
        return f"{minute} {hour} * * *"


@lru_cache(maxsize=1)
def get_service_settings() -> FeedbackSettings:
    return FeedbackSettings()
