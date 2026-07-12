"""Validated settings for the Supabase-backed auth gateway."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from shared.config import Settings

SERVICE_NAME = "auth_service"
SERVICE_TITLE = "HAR Authentication and RBAC Gateway"


class AuthSettings(Settings):
    auth_port: int = Field(default=8005, ge=1, le=65535)
    # Import-safe placeholders keep local tooling able to load the ASGI module.
    # Compose requires real values, and protected requests cannot validate
    # against this non-routable host.
    supabase_url: str = "https://supabase.invalid"
    supabase_publishable_key: str = "not-configured"
    supabase_service_role_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_algorithms: str = "RS256,ES256"
    fusion_internal_url: str = "http://fusion-service:8001"
    feedback_internal_url: str = "http://feedback-service:8002"
    auth_ticket_secret: str = "local-import-only-change-in-env-0000"
    auth_ticket_ttl_seconds: int = Field(default=30, ge=5, le=120)
    auth_upstream_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    # Bootstrap super administrators. Comma-separated emails granted the admin
    # role even before Supabase assigns one, so they can allocate roles to
    # everyone else. Backend-only; never expose with a VITE_ prefix.
    super_admin_emails: str = ""

    @field_validator(
        "supabase_url",
        "supabase_publishable_key",
        "supabase_service_role_key",
        "auth_ticket_secret",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("fusion_internal_url", "feedback_internal_url")
    @classmethod
    def valid_internal_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("internal service URL must be an absolute HTTP(S) URL")
        return value

    @model_validator(mode="after")
    def valid_auth_configuration(self) -> AuthSettings:
        parsed = urlsplit(self.supabase_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("SUPABASE_URL must be an absolute HTTP(S) URL")
        if not self.supabase_publishable_key:
            raise ValueError("SUPABASE_PUBLISHABLE_KEY is required")
        if len(self.auth_ticket_secret) < 32:
            raise ValueError("AUTH_TICKET_SECRET must contain at least 32 characters")
        algorithms = self.jwt_algorithms
        if not algorithms or any(value not in {"RS256", "ES256"} for value in algorithms):
            raise ValueError("SUPABASE_JWT_ALGORITHMS may contain only RS256 and ES256")
        return self

    @property
    def super_admin_email_set(self) -> frozenset[str]:
        return frozenset(
            value.strip().lower()
            for value in self.super_admin_emails.split(",")
            if value.strip()
        )

    @property
    def issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    @property
    def jwt_algorithms(self) -> tuple[str, ...]:
        return tuple(
            value.strip().upper()
            for value in self.supabase_jwt_algorithms.split(",")
            if value.strip()
        )


@lru_cache(maxsize=1)
def get_service_settings() -> AuthSettings:
    return AuthSettings()
