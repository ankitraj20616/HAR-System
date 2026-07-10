"""Sensor service metadata; runtime values come from shared configuration."""

from shared.config import Settings, get_settings

SERVICE_NAME = "sensor_service"
SERVICE_TITLE = "HAR Sensor Service"


def get_service_settings() -> Settings:
    return get_settings()
