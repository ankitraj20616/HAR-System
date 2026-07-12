import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from services.auth_service.config import AuthSettings
from services.auth_service.jwt_verifier import InvalidAccessToken, SupabaseJWTVerifier


def settings() -> AuthSettings:
    return AuthSettings(
        supabase_url="https://project.supabase.co",
        supabase_publishable_key="publishable",
        auth_ticket_secret="t" * 32,
    )


def claims(*, role: str = "caregiver") -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "iss": settings().issuer,
        "aud": "authenticated",
        "sub": "62c74550-e828-4637-abed-fad1cf185d9f",
        "session_id": "6779896d-cc5d-4b65-b40d-6a15aebd0957",
        "email": "user@example.com",
        "user_role": role,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }


def verifier(payload: dict[str, object]) -> SupabaseJWTVerifier:
    instance = SupabaseJWTVerifier(settings())

    async def decode(_token: str):
        return payload

    instance._decode = decode  # type: ignore[method-assign]
    return instance


def test_valid_verified_claims_become_identity() -> None:
    identity = asyncio.run(verifier(claims()).verify("signed-token"))

    assert identity.role == "caregiver"
    assert identity.email == "user@example.com"


@pytest.mark.parametrize("role", ["", "owner", "authenticated"])
def test_unknown_application_role_is_rejected(role: str) -> None:
    with pytest.raises(InvalidAccessToken, match="recognized user role"):
        asyncio.run(verifier(claims(role=role)).verify("signed-token"))


def test_signature_or_standard_claim_failure_is_sanitized() -> None:
    instance = SupabaseJWTVerifier(settings())

    async def reject(_token: str):
        raise ValueError("raw cryptography detail")

    instance._decode = reject  # type: ignore[method-assign]
    with pytest.raises(InvalidAccessToken, match="invalid or expired") as caught:
        asyncio.run(instance.verify("bad-token"))
    assert "cryptography" not in str(caught.value)


def test_verifier_uses_exact_project_issuer_and_asymmetric_algorithms() -> None:
    configured = settings()

    assert configured.issuer == "https://project.supabase.co/auth/v1"
    assert configured.jwks_url.endswith("/auth/v1/.well-known/jwks.json")
    assert configured.jwt_algorithms == ("RS256", "ES256")
