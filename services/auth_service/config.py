"""Validated settings for the local-auth gateway."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator

from shared.config import Settings

SERVICE_NAME = "auth_service"
SERVICE_TITLE = "HAR Authentication and RBAC Gateway"


class AuthSettings(Settings):
    auth_port: int = Field(default=8005, ge=1, le=65535)
    # Local JWT signing secret (at least 32 characters).
    jwt_secret: str = "local-import-only-change-in-env-0000"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = Field(default=60, ge=5, le=1440)
    fusion_internal_url: str = "http://fusion-service:8001"
    feedback_internal_url: str = "http://feedback-service:8002"
    auth_ticket_secret: str = "local-import-only-change-in-env-0000"
    auth_ticket_ttl_seconds: int = Field(default=30, ge=5, le=120)
    auth_upstream_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    # Local CPU-only LLM generation outlives the standard upstream budget, so the
    # feedback generation route proxies with its own longer allowance.
    auth_generate_timeout_seconds: float = Field(default=90.0, gt=0, le=300)
    # Bootstrap super administrators. Comma-separated emails granted the admin
    # role even before the database assigns one, so they can allocate roles to
    # everyone else. Backend-only; never expose with a VITE_ prefix.
    super_admin_emails: str = ""

    @field_validator(
        "jwt_secret",
        "auth_ticket_secret",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("fusion_internal_url", "feedback_internal_url")
    @classmethod
    def valid_internal_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("internal service URL must be an absolute HTTP(S) URL")
        return value

    @property
    def super_admin_email_set(self) -> frozenset[str]:
        return frozenset(
            value.strip().lower()
            for value in self.super_admin_emails.split(",")
            if value.strip()
        )


@lru_cache(maxsize=1)
def get_service_settings() -> AuthSettings:
    return AuthSettings()
