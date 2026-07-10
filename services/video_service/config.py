"""Video service metadata; runtime values come from shared configuration."""

from shared.config import Settings, get_settings

SERVICE_NAME = "video_service"
SERVICE_TITLE = "HAR Video Service"


def get_service_settings() -> Settings:
    return get_settings()
