"""Environment-driven settings shared by backend services."""

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import MESSAGE_SCHEMA_VERSION


class Settings(BaseSettings):
    service_name: str = "har-system"
    service_version: str = "0.1.0"
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    database_url: str = "postgresql://har:har@localhost:5432/hardb"
    log_level: str = "INFO"
    message_schema_version: str = MESSAGE_SCHEMA_VERSION

    sensor_port: int = Field(default=8003, ge=1, le=65535)
    video_port: int = Field(default=8004, ge=1, le=65535)
    fusion_port: int = Field(default=8001, ge=1, le=65535)
    feedback_port: int = Field(default=8002, ge=1, le=65535)

    @field_validator("service_name", "service_version", "mqtt_host")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("setting cannot be empty")
        return value

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @field_validator("message_schema_version")
    @classmethod
    def supported_schema_version(cls, value: str) -> str:
        if value != MESSAGE_SCHEMA_VERSION:
            raise ValueError(f"only MESSAGE_SCHEMA_VERSION={MESSAGE_SCHEMA_VERSION} is supported")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_database_url(cls, value: str) -> str:
        value = value.strip()
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from exc
        if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        if not parsed.path.strip("/"):
            raise ValueError("DATABASE_URL must include a database name")
        if parsed.netloc and parsed.hostname is None:
            raise ValueError("DATABASE_URL must include a valid host")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("DATABASE_URL port must be between 1 and 65535")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()


def clear_settings_cache() -> None:
    """Reset the settings cache, mainly for environment-isolated tests."""

    get_settings.cache_clear()
