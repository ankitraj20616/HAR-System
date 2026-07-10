import asyncio

from services.fusion_service.websocket import WebSocketHub
from shared.schemas import FusedActivity, WebSocketEnvelope


class FakeWebSocket:
    def __init__(self, *, block_send: bool = False) -> None:
        self.accepted = False
        self.closed = False
        self.sent: list[str] = []
        self._gate = asyncio.Event()
        if not block_send:
            self._gate.set()

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, value: str) -> None:
        await self._gate.wait()
        self.sent.append(value)

    async def close(self) -> None:
        self.closed = True
        self._gate.set()


def activity_envelope() -> WebSocketEnvelope:
    return WebSocketEnvelope(
        channel="activity",
        data=FusedActivity(
            ts="2026-06-20T10:00:00Z",
            activity="WALKING",
            confidence=0.9,
            contributors={"sensor": "WALKING"},
        ),
    )


def test_websocket_hub_sends_typed_envelopes_and_cleans_up() -> None:
    async def scenario() -> None:
        hub = WebSocketHub(queue_size=2)
        socket = FakeWebSocket()
        client_id = await hub.connect(socket)  # type: ignore[arg-type]
        assert socket.accepted
        assert hub.active_clients == 1

        await hub.broadcast(activity_envelope())
        await asyncio.sleep(0)

        assert '"channel":"activity"' in socket.sent[0]
        await hub.disconnect(client_id)
        assert hub.active_clients == 0
        assert socket.closed

    asyncio.run(scenario())


def test_slow_client_is_dropped_without_blocking_other_clients() -> None:
    async def scenario() -> None:
        hub = WebSocketHub(queue_size=1)
        slow = FakeWebSocket(block_send=True)
        fast = FakeWebSocket()
        await hub.connect(slow)  # type: ignore[arg-type]
        await hub.connect(fast)  # type: ignore[arg-type]

        # Let the slow sender take the first payload, then fill and overflow its queue.
        await hub.broadcast(activity_envelope())
        await asyncio.sleep(0)
        await hub.broadcast(activity_envelope())
        await asyncio.sleep(0)
        await hub.broadcast(activity_envelope())
        await asyncio.sleep(0)

        assert hub.dropped_clients == 1
        assert hub.active_clients == 1
        assert slow.closed
        assert fast.sent
        await hub.close()

    asyncio.run(scenario())
