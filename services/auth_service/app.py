"""FastAPI entry point for local authentication, RBAC, and protected API forwarding."""

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
from services.auth_service.local_auth import (
    AuthError,
    InvalidAccessToken,
    delete_user,
    get_user_from_token,
    list_users,
    login,
    signup,
    update_user_role,
)
from services.auth_service.models import (
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
    RoleUpdate,
    SignupRequest,
    WebSocketTicketRequest,
    WebSocketTicketResponse,
)
from services.auth_service.proxy import forward_http, forward_websocket
from services.auth_service.rbac import can_open_websocket, is_allowed
from services.auth_service.tickets import InvalidTicket, TicketManager


def create_app(
    settings: AuthSettings | None = None,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    config = settings or get_service_settings()
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
            return await get_user_from_token(authorization[7:].strip(), config)
        except InvalidAccessToken as exc:
            raise HTTPException(
                status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}
            ) from exc

    # ---- Public endpoints (no token required) ----

    @application.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "service": "auth_service",
            "version": config.service_version,
            "status": "healthy",
        }

    @application.post("/api/auth/signup")
    async def signup_endpoint(body: SignupRequest) -> dict[str, Any]:
        try:
            user = await signup(body.email, body.password, config)
            return {"message": "Account created successfully. Please sign in.", "user_id": user["id"]}
        except AuthError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/auth/login", response_model=LoginResponse)
    async def login_endpoint(body: LoginRequest) -> LoginResponse:
        try:
            user, token, expires_in = await login(body.email, body.password, config)
            return LoginResponse(
                access_token=token,
                expires_in=expires_in,
                user=user,
            )
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    # ---- Protected endpoints (token required) ----

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

    @application.get("/api/admin/users")
    async def get_users(
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> list[dict[str, Any]]:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role is required")
        return await list_users(config)

    @application.put("/api/admin/users/{user_id}/role")
    async def update_role(
        user_id: str,
        body: RoleUpdate,
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> dict[str, str]:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role is required")
        try:
            return await update_user_role(user_id, body.role, user.user_id, config)
        except AuthError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.delete("/api/admin/users/{user_id}")
    async def delete_user_route(
        user_id: str,
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> dict[str, str]:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role is required")
        if user_id == user.user_id:
            raise HTTPException(status_code=403, detail="You cannot delete your own account")
        try:
            return await delete_user(user_id, user.user_id, config)
        except AuthError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def protected_proxy(
        path: str,
        request: Request,
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> Response:
        if not is_allowed(user.role, request.method, request.url.path):
            raise HTTPException(status_code=403, detail="Your role does not allow this action")
        is_feedback = request.url.path.startswith("/api/feedback/")
        upstream = config.feedback_internal_url if is_feedback else config.fusion_internal_url
        timeout = (
            config.auth_generate_timeout_seconds
            if request.url.path == "/api/feedback/generate"
            else None
        )
        try:
            return await forward_http(application.state.http, request, upstream, user, timeout)
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
