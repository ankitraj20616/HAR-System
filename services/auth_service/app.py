"""FastAPI entry point for authentication, RBAC, and protected API forwarding."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketException,
    status,
)
from fastapi.responses import Response

from services.auth_service.config import AuthSettings, get_service_settings
from services.auth_service.jwt_verifier import (
    InvalidAccessToken,
    SupabaseJWTVerifier,
    TokenVerifier,
)
from services.auth_service.models import (
    AuthenticatedUser,
    RoleUpdate,
    WebSocketTicketRequest,
    WebSocketTicketResponse,
)
from services.auth_service.proxy import forward_http, forward_websocket
from services.auth_service.rbac import can_open_websocket, is_allowed
from services.auth_service.tickets import InvalidTicket, TicketManager


def create_app(
    settings: AuthSettings | None = None,
    *,
    verifier: TokenVerifier | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    config = settings or get_service_settings()
    token_verifier = verifier or SupabaseJWTVerifier(config)
    tickets = TicketManager(config.auth_ticket_secret, config.auth_ticket_ttl_seconds)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        owns_client = http_client is None
        application.state.http = http_client or httpx.AsyncClient(
            timeout=config.auth_upstream_timeout_seconds,
            follow_redirects=False,
        )
        try:
            yield
        finally:
            if owns_client:
                await application.state.http.aclose()

    application = FastAPI(
        title="HAR Authentication and RBAC Gateway",
        version=config.service_version,
        lifespan=lifespan,
    )

    async def current_user(
        authorization: str | None = Header(default=None),  # noqa: B008
    ) -> AuthenticatedUser:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="A bearer access token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            return await token_verifier.verify(authorization[7:].strip())
        except InvalidAccessToken as exc:
            raise HTTPException(
                status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}
            ) from exc

    @application.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "service": "auth_service",
            "version": config.service_version,
            "status": "healthy",
            "dependencies": {
                "supabase_jwks": {"status": "healthy", "detail": "checked on protected requests"}
            },
        }

    @application.get("/api/auth/config")
    async def public_config() -> dict[str, str]:
        return {
            "supabase_url": config.supabase_url,
            "supabase_publishable_key": config.supabase_publishable_key,
        }

    @application.get("/api/auth/me", response_model=AuthenticatedUser)
    async def me(
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> AuthenticatedUser:
        return user

    @application.post("/api/auth/ws-ticket", response_model=WebSocketTicketResponse)
    async def websocket_ticket(
        body: WebSocketTicketRequest,
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> WebSocketTicketResponse:
        if not can_open_websocket(user.role):
            raise HTTPException(status_code=403, detail="Your role cannot open live monitoring")
        return WebSocketTicketResponse(
            ticket=tickets.issue(user, body.target), expires_in=config.auth_ticket_ttl_seconds
        )

    @application.put("/api/admin/users/{user_id}/role")
    async def update_role(
        user_id: str,
        body: RoleUpdate,
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> dict[str, str]:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role is required")
        if not config.supabase_service_role_key:
            raise HTTPException(status_code=503, detail="Role administration is not configured")
        response = await application.state.http.post(
            f"{config.supabase_url}/rest/v1/user_roles",
            headers={
                "apikey": config.supabase_service_role_key,
                "Authorization": f"Bearer {config.supabase_service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
            json={"user_id": user_id, "role": body.role, "updated_by": user.user_id},
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase rejected the role update")
        return {"user_id": user_id, "role": body.role}

    @application.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def protected_proxy(
        path: str,
        request: Request,
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> Response:
        if not is_allowed(user.role, request.method, request.url.path):
            raise HTTPException(status_code=403, detail="Your role does not allow this action")
        upstream = (
            config.feedback_internal_url
            if request.url.path.startswith("/api/feedback/")
            else config.fusion_internal_url
        )
        try:
            return await forward_http(application.state.http, request, upstream, user)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503, detail="Requested HAR service is unavailable"
            ) from exc

    async def websocket_gateway(socket: WebSocket, target: str) -> None:
        ticket = socket.query_params.get("ticket", "")
        try:
            tickets.consume(ticket, target)  # type: ignore[arg-type]
        except InvalidTicket as exc:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc)) from exc
        upstream = (
            config.fusion_internal_url if target == "fusion" else config.feedback_internal_url
        )
        ws_upstream = (
            upstream.replace("http://", "ws://", 1).replace("https://", "wss://", 1) + "/ws"
        )
        try:
            await forward_websocket(socket, ws_upstream)
        except Exception:
            if socket.client_state.name != "DISCONNECTED":
                await socket.close(code=1011, reason="Live service is unavailable")

    @application.websocket("/ws")
    async def fusion_websocket(socket: WebSocket) -> None:
        await websocket_gateway(socket, "fusion")

    @application.websocket("/feedback-ws")
    async def feedback_websocket(socket: WebSocket) -> None:
        await websocket_gateway(socket, "feedback")

    return application


app = create_app()
