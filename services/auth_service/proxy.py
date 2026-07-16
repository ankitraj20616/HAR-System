"""HTTP and WebSocket forwarding after authentication has succeeded."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import httpx
from fastapi import Request, WebSocket
from fastapi.responses import Response

from services.auth_service.models import AuthenticatedUser

DROP_REQUEST_HEADERS = {
    "authorization",
    "connection",
    "content-length",
    "host",
    "transfer-encoding",
    "upgrade",
    "x-har-user-id",
    "x-har-user-role",
}
DROP_RESPONSE_HEADERS = {"connection", "content-encoding", "content-length", "transfer-encoding"}


async def forward_http(
    client: httpx.AsyncClient,
    request: Request,
    upstream: str,
    user: AuthenticatedUser,
    timeout: float | None = None,
) -> Response:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in DROP_REQUEST_HEADERS
    }
    headers["X-HAR-User-ID"] = user.user_id
    headers["X-HAR-User-Role"] = user.role
    response = await client.request(
        request.method,
        f"{upstream}{request.url.path}",
        params=request.query_params,
        content=await request.body(),
        headers=headers,
        **({} if timeout is None else {"timeout": timeout}),
    )
    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in DROP_RESPONSE_HEADERS
    }
    return Response(
        response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )


async def forward_websocket(client_socket: WebSocket, upstream_url: str) -> None:
    import websockets

    async with websockets.connect(upstream_url, open_timeout=5, close_timeout=3) as upstream:
        await client_socket.accept()

        async def client_to_upstream() -> None:
            while True:
                message = await client_socket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                if message.get("text") is not None:
                    await upstream.send(message["text"])
                elif message.get("bytes") is not None:
                    await upstream.send(message["bytes"])

        async def upstream_to_client() -> None:
            async for message in upstream:
                if isinstance(message, bytes):
                    await client_socket.send_bytes(message)
                else:
                    await client_socket.send_text(message)

        tasks = {
            asyncio.create_task(client_to_upstream()),
            asyncio.create_task(upstream_to_client()),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done | pending:
            with suppress(asyncio.CancelledError, Exception):
                await task
