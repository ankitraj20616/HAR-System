"""Bounded non-blocking WebSocket fan-out for feedback consumers."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass

from fastapi import WebSocket

from shared.schemas import WebSocketEnvelope


@dataclass
class _Client:
    socket: WebSocket
    queue: asyncio.Queue[str]
    sender: asyncio.Task[None]


class WebSocketHub:
    def __init__(self, queue_size: int = 64) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        self._queue_size = queue_size
        self._clients: dict[int, _Client] = {}
        self._next_id = 1
        self.dropped_clients = 0

    @property
    def active_clients(self) -> int:
        return len(self._clients)

    async def connect(self, socket: WebSocket) -> int:
        await socket.accept()
        client_id = self._next_id
        self._next_id += 1
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._queue_size)
        sender = asyncio.create_task(self._send(client_id, socket, queue))
        self._clients[client_id] = _Client(socket, queue, sender)
        return client_id

    async def disconnect(self, client_id: int) -> None:
        client = self._clients.pop(client_id, None)
        if client is None:
            return
        if client.sender is not asyncio.current_task():
            client.sender.cancel()
            with suppress(asyncio.CancelledError):
                await client.sender
        with suppress(Exception):
            await client.socket.close()

    async def broadcast(self, envelope: WebSocketEnvelope) -> None:
        payload = envelope.model_dump_json()
        overflowed: list[int] = []
        for client_id, client in tuple(self._clients.items()):
            try:
                client.queue.put_nowait(payload)
            except asyncio.QueueFull:
                overflowed.append(client_id)
        for client_id in overflowed:
            self.dropped_clients += 1
            await self.disconnect(client_id)

    async def close(self) -> None:
        for client_id in tuple(self._clients):
            await self.disconnect(client_id)

    async def _send(self, client_id: int, socket: WebSocket, queue: asyncio.Queue[str]) -> None:
        try:
            while True:
                await socket.send_text(await queue.get())
                queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception:
            self._clients.pop(client_id, None)
