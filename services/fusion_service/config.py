"""Fusion service metadata; runtime values come from shared configuration."""

from shared.config import Settings, get_settings

SERVICE_NAME = "fusion_service"
SERVICE_TITLE = "HAR Fusion Service"


def get_service_settings() -> Settings:
    return get_settings()
