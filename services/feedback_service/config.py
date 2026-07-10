"""Feedback service metadata; runtime values come from shared configuration."""

from shared.config import Settings, get_settings

SERVICE_NAME = "feedback_service"
SERVICE_TITLE = "HAR Feedback Service"


def get_service_settings() -> Settings:
    return get_settings()
