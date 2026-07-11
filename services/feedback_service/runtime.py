"""MQTT event ingestion, persistence, idempotency, and publication runtime."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from functools import partial
from threading import Event
from typing import Any

from pydantic import ValidationError

from services.feedback_service.config import FeedbackSettings
from services.feedback_service.digest import build_digest, event_digest
from services.feedback_service.engine import FeedbackEngine, GenerationResult
from services.feedback_service.llm import FeedbackProvider, OllamaProvider
from services.feedback_service.websocket import WebSocketHub
from services.runtime import DependencyHealth
from shared.db import ActivityRepository, EventRepository, FeedbackRepository, initialize_database
from shared.schemas import Feedback, HAREvent, WebSocketEnvelope
from shared.topics import EVENT, FEEDBACK, policy_for


async def run_blocking(function: Any, *args: Any, **kwargs: Any) -> Any:
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="feedback-io")
    try:
        return await asyncio.get_running_loop().run_in_executor(
            executor, partial(function, *args, **kwargs)
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def feedback_from_row(row: dict[str, Any]) -> Feedback:
    payload = row.get("payload")
    if isinstance(payload, str):
        import json

        payload = json.loads(payload)
    if isinstance(payload, dict):
        return Feedback.model_validate(payload)
    return Feedback(
        ts=row["ts"],
        mode=row["mode"],
        headline=row["headline"],
        detail=row["detail"],
        severity=row["severity"],
        recommendations=[],
        disclaimer="This is automated assistive information, not a medical diagnosis.",
    )


class FeedbackRuntime:
    name = "mqtt"

    def __init__(
        self,
        settings: FeedbackSettings,
        *,
        provider: FeedbackProvider | None = None,
        activity_repository: ActivityRepository | None = None,
        event_repository: EventRepository | None = None,
        feedback_repository: FeedbackRepository | None = None,
        websocket_hub: WebSocketHub | None = None,
        client_factory: Any | None = None,
        connect_timeout: float = 1.0,
    ) -> None:
        self.settings = settings
        self.engine = FeedbackEngine(
            provider
            or OllamaProvider(
                settings.ollama_host, settings.llm_model, settings.generation_timeout
            ),
            fallback_enabled=settings.feedback_fallback_enabled,
        )
        self.activity_repository = activity_repository or ActivityRepository(settings.database_url)
        self.event_repository = event_repository or EventRepository(settings.database_url)
        self.feedback_repository = feedback_repository or FeedbackRepository(settings.database_url)
        self.websocket_hub = websocket_hub or WebSocketHub(settings.feedback_websocket_queue_size)
        self._client_factory = client_factory
        self._connect_timeout = connect_timeout
        self._client: Any | None = None
        self._connected = Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[HAREvent] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._periodic_worker: asyncio.Task[None] | None = None
        self._retry_worker: asyncio.Task[None] | None = None
        self._summary_worker: asyncio.Task[None] | None = None
        self._enqueue_tasks: set[asyncio.Task[None]] = set()
        self._pending_feedback: dict[str, Feedback] = {}
        self._database_healthy = True
        self.counters = {
            "validation_failures": 0,
            "duplicates": 0,
            "generated": 0,
            "processing_failures": 0,
            "queue_backpressure": 0,
            "publish_failures": 0,
        }

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=self.settings.feedback_input_queue_size)
        try:
            await run_blocking(initialize_database, self.settings.database_url)
            self._database_healthy = True
        except Exception:
            self._database_healthy = False
        self._worker = asyncio.create_task(self._run(), name="feedback-runtime")
        self._periodic_worker = asyncio.create_task(
            self._run_periodic_feedback(), name="feedback-periodic"
        )
        self._retry_worker = asyncio.create_task(
            self._run_pending_retries(), name="feedback-persistence-retry"
        )
        self._summary_worker = asyncio.create_task(
            self._run_scheduled_summaries(), name="feedback-daily-summary"
        )
        try:
            await run_blocking(self._start_client)
            await run_blocking(self._connected.wait, self._connect_timeout)
        except Exception:
            # API and deterministic fallback remain available while MQTT reconnects.
            pass

    def _start_client(self) -> None:
        if self._client_factory is None:
            import paho.mqtt.client as mqtt

            try:
                client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id="har-feedback_service",
                    protocol=mqtt.MQTTv311,
                )
            except (AttributeError, TypeError):
                client = mqtt.Client(client_id="har-feedback_service", protocol=mqtt.MQTTv311)
        else:
            client = self._client_factory()
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        if hasattr(client, "reconnect_delay_set"):
            client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client = client
        client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)
        client.loop_start()

    def _on_connect(
        self, client: Any, _userdata: Any, _flags: Any, reason: Any, *args: Any
    ) -> None:
        if getattr(reason, "value", reason) == 0:
            policy = policy_for(EVENT)
            client.subscribe(policy.topic, qos=policy.qos)
            self._connected.set()

    def _on_disconnect(self, _client: Any, _userdata: Any, *args: Any) -> None:
        self._connected.clear()

    def _on_message(self, _client: Any, _userdata: Any, message: Any) -> None:
        if message.topic != EVENT:
            return
        try:
            event = HAREvent.model_validate_json(message.payload)
        except (ValidationError, ValueError, TypeError):
            self.counters["validation_failures"] += 1
            return
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._enqueue, event)

    def _enqueue(self, event: HAREvent) -> None:
        if self._queue is None:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Never discard a validated safety event. Keep a bounded-queue put
            # pending on the event loop so MQTT callback processing stays fast.
            self.counters["queue_backpressure"] += 1
            task = asyncio.create_task(self._queue.put(event))
            self._enqueue_tasks.add(task)
            task.add_done_callback(self._enqueue_tasks.discard)

    async def _run(self) -> None:
        assert self._queue is not None
        while True:
            event = await self._queue.get()
            try:
                try:
                    await self._flush_pending()
                    await self.process_event(event)
                except Exception:
                    self.counters["processing_failures"] += 1
                    self._database_healthy = False
            finally:
                self._queue.task_done()

    async def _run_periodic_feedback(self) -> None:
        while True:
            await asyncio.sleep(self.settings.feedback_interval)
            from_ts, to_ts = self.default_range()
            try:
                await self._flush_pending()
                await self.generate_period("feedback", from_ts, to_ts)
            except Exception:
                self.counters["processing_failures"] += 1

    async def _run_pending_retries(self) -> None:
        while True:
            await asyncio.sleep(5)
            if self._pending_feedback:
                await self._flush_pending()

    async def _run_scheduled_summaries(self) -> None:
        minute, hour = (int(value) for value in self.settings.summary_schedule.split()[:2])
        while True:
            now = datetime.now(UTC)
            scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled <= now:
                scheduled += timedelta(days=1)
            await asyncio.sleep((scheduled - now).total_seconds())
            from_ts = scheduled - timedelta(hours=self.settings.feedback_default_period_hours)
            try:
                await self.generate_period(
                    "summary",
                    from_ts,
                    scheduled,
                    request_id=f"daily:{scheduled.date().isoformat()}",
                )
            except Exception:
                self.counters["processing_failures"] += 1

    async def process_event(self, event: HAREvent) -> Feedback:
        key = f"event:{event.type}:{event.ts.isoformat()}"
        pending = self._pending_feedback.get(key)
        if pending is not None:
            self.counters["duplicates"] += 1
            return pending
        try:
            existing = await self.find_by_key(key)
        except Exception:
            self._database_healthy = False
            existing = None
        if existing is not None:
            self.counters["duplicates"] += 1
            return feedback_from_row(existing)

        # Safety notification is deterministic, persisted and published before
        # local model inference begins, so a slow CPU model cannot delay it.
        from services.feedback_service.fallback import deterministic_feedback

        template = FeedbackEngine._wire(
            "alert", deterministic_feedback("alert", event_digest(event))
        )
        # Publish first: a database outage must never delay a critical banner.
        await self._publish(template)
        try:
            await run_blocking(self.feedback_repository.add, template, key)
            self._database_healthy = True
        except Exception:
            self._database_healthy = False
            self._pending_feedback[key] = template
        self.counters["generated"] += 1
        return template

    async def _flush_pending(self) -> None:
        for key, feedback in tuple(self._pending_feedback.items()):
            try:
                await run_blocking(self.feedback_repository.add, feedback, key)
            except Exception:
                self._database_healthy = False
                return
            self._pending_feedback.pop(key, None)
            self._database_healthy = True

    async def generate_period(
        self, mode: str, from_ts: datetime, to_ts: datetime, request_id: str | None = None
    ) -> tuple[GenerationResult, bool]:
        key = f"request:{request_id}" if request_id else None
        if key:
            existing = await self.find_by_key(key)
            if existing is not None:
                return GenerationResult(feedback_from_row(existing), False, "ok"), True
        activities, events, aggregates = await asyncio.gather(
            run_blocking(self.activity_repository.between, from_ts, to_ts, 1000),
            run_blocking(self.event_repository.between, from_ts, to_ts, 1000),
            run_blocking(self.activity_repository.trends, from_ts, to_ts, 5.0),
        )
        digest = build_digest(
            from_ts,
            to_ts,
            activities,
            events,
            maximum_size=self.settings.maximum_digest_size,
            aggregates=aggregates,
        )
        result = await self.engine.generate(mode, digest)
        await self.persist_and_publish(result.feedback, key)
        self.counters["generated"] += 1
        return result, False

    async def latest(self) -> Feedback | None:
        row = await run_blocking(self.feedback_repository.latest)
        return feedback_from_row(row) if row else None

    async def find_by_key(self, key: str) -> dict[str, Any] | None:
        finder = getattr(self.feedback_repository, "by_idempotency_key", None)
        return await run_blocking(finder, key) if callable(finder) else None

    async def persist_and_publish(self, feedback: Feedback, key: str | None = None) -> None:
        try:
            await run_blocking(self.feedback_repository.add, feedback, key)
        except TypeError:  # compatibility with pre-M4 repository fakes
            await run_blocking(self.feedback_repository.add, feedback)
        self._database_healthy = True
        await self._publish(feedback)

    async def _publish(self, feedback: Feedback) -> None:
        client = self._client
        if client is not None and self._connected.is_set():
            policy = policy_for(FEEDBACK)
            result = client.publish(
                policy.topic,
                payload=feedback.model_dump_json(),
                qos=policy.qos,
                retain=policy.retain,
            )
            result_code = getattr(result, "rc", result[0] if isinstance(result, tuple) else 0)
            if result_code not in (None, 0):
                self.counters["publish_failures"] += 1
        await self.websocket_hub.broadcast(WebSocketEnvelope(channel="feedback", data=feedback))

    def default_range(self) -> tuple[datetime, datetime]:
        end = datetime.now(UTC)
        return end - timedelta(hours=self.settings.feedback_default_period_hours), end

    def health(self) -> DependencyHealth:
        healthy = self._connected.is_set() and self._database_healthy
        return DependencyHealth(
            status="healthy" if healthy else "degraded",
            detail="connected; persistence ready" if healthy else "MQTT or persistence unavailable",
        )

    async def stop(self) -> None:
        for task in tuple(self._enqueue_tasks):
            task.cancel()
        if self._enqueue_tasks:
            await asyncio.gather(*self._enqueue_tasks, return_exceptions=True)
        self._enqueue_tasks.clear()
        if self._summary_worker is not None:
            self._summary_worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._summary_worker
            self._summary_worker = None
        if self._retry_worker is not None:
            self._retry_worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._retry_worker
            self._retry_worker = None
        if self._periodic_worker is not None:
            self._periodic_worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._periodic_worker
            self._periodic_worker = None
        if self._worker is not None:
            self._worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None
        client, self._client = self._client, None
        self._connected.clear()
        if client is not None:
            with suppress(Exception):
                client.disconnect()
            with suppress(Exception):
                client.loop_stop()
        await self.websocket_hub.close()
