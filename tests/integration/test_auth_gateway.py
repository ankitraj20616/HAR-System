import asyncio

import httpx

from services.auth_service.app import create_app
from services.auth_service.config import AuthSettings
from services.auth_service.jwt_verifier import InvalidAccessToken
from services.auth_service.models import AuthenticatedUser


class FakeVerifier:
    async def verify(self, token: str) -> AuthenticatedUser:
        if token == "invalid":
            raise InvalidAccessToken("access token is invalid or expired")
        role = token if token in {"pending", "caregiver", "doctor", "admin"} else "caregiver"
        return AuthenticatedUser(
            user_id="832b4b2d-949b-4260-b4b6-08a36f426ec1",
            email="user@example.com",
            role=role,
            session_id="2cbb800f-1a27-4d10-918e-068f01611996",
        )


def config(**changes) -> AuthSettings:
    return AuthSettings(
        supabase_url="https://project.supabase.co",
        supabase_publishable_key="publishable",
        auth_ticket_secret="s" * 32,
        fusion_internal_url="http://fusion.internal",
        feedback_internal_url="http://feedback.internal",
        **changes,
    )


async def request(
    path: str,
    *,
    token: str | None = None,
    method: str = "GET",
    json=None,
    settings: AuthSettings | None = None,
):
    seen = {}

    async def upstream_handler(upstream_request: httpx.Request) -> httpx.Response:
        seen["url"] = str(upstream_request.url)
        seen["headers"] = dict(upstream_request.headers)
        return httpx.Response(200, json={"upstream": upstream_request.url.host})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    app = create_app(settings or config(), verifier=FakeVerifier(), http_client=upstream)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    headers.update({"X-HAR-User-ID": "spoofed", "X-HAR-User-Role": "admin"})
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.request(method, path, headers=headers, json=json)
    await upstream.aclose()
    return response, seen


def test_missing_and_invalid_tokens_return_401() -> None:
    missing, _ = asyncio.run(request("/api/status"))
    invalid, _ = asyncio.run(request("/api/status", token="invalid"))

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"


def test_pending_and_wrong_role_return_403() -> None:
    pending, _ = asyncio.run(request("/api/status", token="pending"))
    doctor_ack, _ = asyncio.run(request("/api/events/7/ack", token="doctor", method="POST"))

    assert pending.status_code == 403
    assert doctor_ack.status_code == 403


def test_allowed_request_routes_upstream_and_replaces_spoofed_identity() -> None:
    response, seen = asyncio.run(request("/api/status?detail=true", token="caregiver"))

    assert response.status_code == 200
    assert seen["url"] == "http://fusion.internal/api/status?detail=true"
    assert seen["headers"]["x-har-user-id"] == "832b4b2d-949b-4260-b4b6-08a36f426ec1"
    assert seen["headers"]["x-har-user-role"] == "caregiver"
    assert "authorization" not in seen["headers"]


def test_feedback_routes_to_feedback_service() -> None:
    response, seen = asyncio.run(
        request(
            "/api/feedback/generate",
            token="doctor",
            method="POST",
            json={"mode": "summary", "period": "24h", "request_id": "abc"},
        )
    )

    assert response.status_code == 200
    assert seen["url"] == "http://feedback.internal/api/feedback/generate"


def test_websocket_ticket_requires_approved_role() -> None:
    denied, _ = asyncio.run(
        request(
            "/api/auth/ws-ticket",
            token="pending",
            method="POST",
            json={"target": "fusion"},
        )
    )
    allowed, _ = asyncio.run(
        request(
            "/api/auth/ws-ticket",
            token="caregiver",
            method="POST",
            json={"target": "fusion"},
        )
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["expires_in"] == 30


def test_role_administration_is_admin_only_and_requires_server_key() -> None:
    denied, _ = asyncio.run(
        request(
            "/api/admin/users/832b4b2d-949b-4260-b4b6-08a36f426ec1/role",
            token="caregiver",
            method="PUT",
            json={"role": "doctor"},
        )
    )
    unconfigured, _ = asyncio.run(
        request(
            "/api/admin/users/832b4b2d-949b-4260-b4b6-08a36f426ec1/role",
            token="admin",
            method="PUT",
            json={"role": "doctor"},
        )
    )

    assert denied.status_code == 403
    assert unconfigured.status_code == 503


def test_admin_can_update_role_without_secret_in_response() -> None:
    configured = config(supabase_service_role_key="server-secret")
    response, seen = asyncio.run(
        request(
            "/api/admin/users/832b4b2d-949b-4260-b4b6-08a36f426ec1/role",
            token="admin",
            method="PUT",
            json={"role": "doctor"},
            settings=configured,
        )
    )

    assert response.status_code == 200
    assert response.json()["role"] == "doctor"
    assert "server-secret" not in response.text
    assert seen["url"] == "https://project.supabase.co/rest/v1/user_roles"


def test_public_browser_config_never_contains_backend_secrets() -> None:
    configured = config(supabase_service_role_key="server-secret")
    response, _ = asyncio.run(request("/api/auth/config", settings=configured))

    assert response.status_code == 200
    assert response.json() == {
        "supabase_url": "https://project.supabase.co",
        "supabase_publishable_key": "publishable",
    }
    assert "server-secret" not in response.text
