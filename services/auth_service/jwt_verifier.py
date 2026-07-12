"""Supabase access-token verification using asymmetric JWKS signing keys."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

import httpx

from services.auth_service.config import AuthSettings
from services.auth_service.models import AuthenticatedUser


class InvalidAccessToken(ValueError):
    """Raised when a bearer token is missing required trust or identity claims."""


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> AuthenticatedUser: ...


class SupabaseJWTVerifier:
    """Fetch public keys asynchronously and cache them for at most ten minutes."""

    def __init__(self, settings: AuthSettings) -> None:
        self.settings = settings
        self._keys: dict[str, Any] = {}
        self._keys_expire_at = 0.0
        self._refresh_lock = asyncio.Lock()

    async def verify(self, token: str) -> AuthenticatedUser:
        try:
            claims = await self._decode(token)
            email = claims.get("email")
            role = claims.get("user_role")
            # Bootstrap super administrators by verified email. Their signed token
            # is trusted for the admin role even before Supabase assigns one, so
            # they can allocate roles to everyone else.
            normalized_email = email.strip().lower() if isinstance(email, str) else ""
            if normalized_email in self.settings.super_admin_email_set:
                role = "admin"
            if role not in {"pending", "caregiver", "doctor", "admin"}:
                raise InvalidAccessToken("access token has no recognized user role")
            return AuthenticatedUser(
                user_id=str(claims["sub"]),
                email=email,
                role=role,
                session_id=str(claims["session_id"]),
            )
        except InvalidAccessToken:
            raise
        except Exception as exc:
            raise InvalidAccessToken("access token is invalid or expired") from exc

    async def _decode(self, token: str) -> dict[str, Any]:
        import jwt

        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        key_id = header.get("kid")
        if algorithm not in self.settings.jwt_algorithms or not isinstance(key_id, str):
            raise InvalidAccessToken("access token uses an unsupported signing key")
        key = await self._get_key(key_id)
        return jwt.decode(
            token,
            key,
            algorithms=list(self.settings.jwt_algorithms),
            audience=self.settings.supabase_jwt_audience,
            issuer=self.settings.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "session_id"]},
        )

    async def _get_key(self, key_id: str) -> Any:
        now = time.monotonic()
        if now >= self._keys_expire_at:
            await self._refresh_keys()
        elif key_id not in self._keys:
            # A new standby/current key may appear before the normal cache TTL.
            await self._refresh_keys(force=True)
        try:
            return self._keys[key_id]
        except KeyError as exc:
            raise InvalidAccessToken("access token signing key is not trusted") from exc

    async def _refresh_keys(self, *, force: bool = False) -> None:
        async with self._refresh_lock:
            if not force and time.monotonic() < self._keys_expire_at and self._keys:
                return
            import jwt

            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await client.get(self.settings.jwks_url)
                response.raise_for_status()
            jwk_set = jwt.PyJWKSet.from_dict(response.json())
            keys = {
                key.key_id: key.key
                for key in jwk_set.keys
                if key.key_id and key.algorithm_name in self.settings.jwt_algorithms
            }
            if not keys:
                raise InvalidAccessToken("Supabase returned no supported signing keys")
            self._keys = keys
            self._keys_expire_at = time.monotonic() + 600
