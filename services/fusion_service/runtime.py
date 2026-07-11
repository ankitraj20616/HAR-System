"""MQTT ingestion and authoritative persistence orchestration for Fusion."""

from __future__ import annotations

import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from threading import Event, Lock
from typing import Any, Literal

from pydantic import ValidationError

from services.fusion_service.config import FusionSettings
from services.fusion_service.fusion import FusionDecision, FusionEngine
from services.fusion_service.models import (
    ComponentStatus,
    FusionStatusResponse,
    ModalityStatus,
)
from services.fusion_service.safety import SafetyEngine
from services.fusion_service.websocket import WebSocketHub
from services.runtime import DependencyHealth
from shared.db import (
    ActivityRepository,
    EventRepository,
    initialize_database,
)
from shared.labels import ActivityLabel
from shared.logging import get_logger
from shared.schemas import (
    FusedActivity,
    HAREvent,
    SensorPrediction,
    VideoPrediction,
    WebSocketEnvelope,
)
from shared.topics import (
    ACTIVITY,
    EVENT,
    SENSOR_PREDICTION,
    VIDEO_PREDICTION,
    policy_for,
)

logger = get_logger(__name__)
Prediction = SensorPrediction | VideoPrediction
Output = FusedActivity | HAREvent
Channel = Literal["activity", "event"]


async def run_blocking(function: Any, *args: Any) -> Any:
    """Run one synchronous repository operation away from the event loop.

    A short-lived executor is intentional here: it avoids sharing psycopg
    connections between async request tasks and keeps shutdown deterministic.
    """

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fusion-db")
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, partial(function, *args))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


@dataclass
class _PendingOutput:
    channel: Channel
    payload: Output


class FusionMQTTDependency:
    """Consume both modality streams and publish persisted Fusion outputs.

    Paho callbacks only validate and enqueue. All fusion, database, and
    WebSocket work stays on the application's asyncio loop.
    """

    name = "mqtt"

    def __init__(
        self,
        settings: FusionSettings,
        *,
        engine: FusionEngine | None = None,
        safety: SafetyEngine | None = None,
        activity_repository: ActivityRepository | None = None,
        event_repository: EventRepository | None = None,
        websocket_hub: WebSocketHub | None = None,
        client_factory: Any | None = None,
        connect_timeout: float = 1.0,
    ) -> None:
        self.settings = settings
        self.engine = engine or FusionEngine(settings)
        self.safety = safety or SafetyEngine(
            fall_accel_threshold=settings.fall_accel_threshold,
            fall_correlation_ms=settings.fall_correlation_ms,
            fall_cooldown_seconds=settings.fall_cooldown_seconds,
            fall_recovery_timeout_seconds=settings.fall_recovery_timeout_seconds,
            inactivity_seconds=settings.inactivity_seconds,
            inactivity_motion_threshold=settings.inactivity_motion_threshold,
            abnormal_min_seconds=settings.abnormal_min_seconds,
            abnormal_baseline_samples=settings.abnormal_baseline_samples,
            abnormal_baseline_multiplier=settings.abnormal_baseline_multiplier,
        )
        self.activity_repository = activity_repository or ActivityRepository(settings.database_url)
        self.event_repository = event_repository or EventRepository(settings.database_url)
        self.websocket_hub = websocket_hub or WebSocketHub(settings.websocket_queue_size)
        self._client_factory = client_factory
        self._connect_timeout = connect_timeout
        self._client: Any | None = None
        self._connected = Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._input_queue: asyncio.Queue[Prediction] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._pending: deque[_PendingOutput] = deque(maxlen=settings.input_queue_size)
        self._state_lock = Lock()
        self._database_healthy = True
        self._database_detail: str | None = None
        self._last_receipt: dict[str, datetime | None] = {"sensor": None, "video": None}
        self._last_source: dict[str, datetime | None] = {"sensor": None, "video": None}
        self._current_activity: FusedActivity | None = None
        self.counters: dict[str, int] = {
            "validation_failures": 0,
            "queue_drops": 0,
            "activities": 0,
            "events": 0,
            "database_failures": 0,
            "publish_failures": 0,
        }

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._input_queue = asyncio.Queue(maxsize=self.settings.input_queue_size)
        # Apply the repeatable schema here so existing named volumes receive M3
        # idempotency indexes, not only fresh Docker databases.
        try:
            await run_blocking(initialize_database, self.settings.database_url)
            self._set_database_health(True, "schema ready")
            latest_reader = getattr(self.activity_repository, "latest", None)
            latest = latest_reader() if callable(latest_reader) else None
            if latest is not None:
                self._current_activity = FusedActivity(
                    ts=latest["ts"],
                    activity=latest["activity"],
                    confidence=latest["confidence"],
                    contributors={
                        "sensor": latest.get("sensor_label"),
                        "video": latest.get("video_label"),
                    },
                )
        except Exception as exc:
            self._record_database_failure(exc)

        self._worker = asyncio.create_task(self._run(), name="fusion-runtime")
        self._connected.clear()
        try:
            await asyncio.to_thread(self._start_client)
            connected = await asyncio.to_thread(
                self._connected.wait,
                self._connect_timeout,
            )
            if not connected:
                logger.warning(
                    "MQTT broker unavailable; reconnecting in background",
                    extra={"event": "fusion_mqtt_degraded"},
                )
        except Exception as exc:
            logger.error(
                f"MQTT startup failed ({type(exc).__name__})",
                extra={"event": "fusion_mqtt_start_failed"},
            )

    def _start_client(self) -> None:
        if self._client_factory is None:
            import paho.mqtt.client as mqtt

            try:
                client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id="har-fusion_service",
                    protocol=mqtt.MQTTv311,
                )
            except (AttributeError, TypeError):
                client = mqtt.Client(client_id="har-fusion_service", protocol=mqtt.MQTTv311)
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
        reason_code = getattr(reason, "value", reason)
        if reason_code != 0:
            self._connected.clear()
            return
        for topic in (SENSOR_PREDICTION, VIDEO_PREDICTION):
            policy = policy_for(topic)
            client.subscribe(policy.topic, qos=policy.qos)
        self._connected.set()

    def _on_disconnect(self, _client: Any, _userdata: Any, *args: Any) -> None:
        self._connected.clear()

    def _on_message(self, _client: Any, _userdata: Any, message: Any) -> None:
        try:
            if message.topic == SENSOR_PREDICTION:
                prediction: Prediction = SensorPrediction.model_validate_json(message.payload)
            elif message.topic == VIDEO_PREDICTION:
                prediction = VideoPrediction.model_validate_json(message.payload)
            else:
                return
        except (ValidationError, ValueError, TypeError):
            self.counters["validation_failures"] += 1
            logger.warning(
                "Fusion prediction contract rejected",
                extra={"event": "fusion_payload_rejected"},
            )
            return
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(self._enqueue, prediction)

    def _enqueue(self, prediction: Prediction) -> None:
        queue = self._input_queue
        if queue is None:
            return
        try:
            queue.put_nowait(prediction)
        except asyncio.QueueFull:
            self.counters["queue_drops"] += 1
            logger.warning(
                "Fusion input queue full; newest prediction dropped",
                extra={"event": "fusion_input_queue_full"},
            )

    async def _run(self) -> None:
        queue = self._input_queue
        if queue is None:
            return
        loop = asyncio.get_running_loop()
        next_tick = loop.time() + self.settings.fusion_interval
        try:
            while True:
                timeout = max(0.0, next_tick - loop.time())
                try:
                    prediction = await asyncio.wait_for(queue.get(), timeout=timeout)
                except TimeoutError:
                    prediction = None
                if prediction is not None:
                    try:
                        await self.process_prediction(prediction)
                    finally:
                        queue.task_done()
                if loop.time() >= next_tick:
                    await self.process_interval(datetime.now(UTC))
                    await self._retry_pending()
                    next_tick = loop.time() + self.settings.fusion_interval
        except asyncio.CancelledError:
            raise

    async def process_prediction(self, prediction: Prediction) -> None:
        result = self.engine.add(prediction)
        if not result.accepted:
            return
        modality = str(prediction.modality)
        with self._state_lock:
            self._last_receipt[modality] = datetime.now(UTC)
            self._last_source[modality] = prediction.ts
        for event in self.safety.process_prediction(prediction):
            await self._persist_and_publish("event", event)

    async def process_interval(self, now: datetime | None = None) -> FusionDecision | None:
        decision = self.engine.fuse(now or datetime.now(UTC))
        if decision is None:
            return None
        persisted = await self._persist_and_publish("activity", decision.activity)
        if persisted:
            with self._state_lock:
                self._current_activity = decision.activity
            for event in self.safety.process_activity(decision.activity, decision.sensor):
                await self._persist_and_publish("event", event)
        logger.info(
            "Fusion interval completed",
            extra={"event": "fusion_decision"},
        )
        return decision

    async def _persist_and_publish(self, channel: Channel, payload: Output) -> bool:
        try:
            repository = (
                self.activity_repository if channel == "activity" else self.event_repository
            )
            await run_blocking(repository.add, payload)
            self._set_database_health(True, "last write succeeded")
            if channel == "activity" and isinstance(payload, FusedActivity):
                with self._state_lock:
                    self._current_activity = payload
        except Exception as exc:
            self._record_database_failure(exc)
            self._pending.append(_PendingOutput(channel, payload))
            return False

        await self._publish(channel, payload)
        self.counters["activities" if channel == "activity" else "events"] += 1
        return True

    async def _retry_pending(self) -> None:
        for _ in range(len(self._pending)):
            pending = self._pending.popleft()
            if not await self._persist_and_publish(pending.channel, pending.payload):
                # _persist_and_publish appended it at the tail; stop hammering a
                # database that is still unavailable until the next interval.
                break

    async def _publish(self, channel: Channel, payload: Output) -> None:
        topic = ACTIVITY if channel == "activity" else EVENT
        client = self._client
        if client is not None and self._connected.is_set():
            policy = policy_for(topic)
            try:
                result = client.publish(
                    policy.topic,
                    payload=payload.model_dump_json(),
                    qos=policy.qos,
                    retain=policy.retain,
                )
                if getattr(result, "rc", 0) != 0:
                    raise ConnectionError("MQTT publish returned a failure code")
            except Exception as exc:
                self.counters["publish_failures"] += 1
                logger.warning(
                    f"Fusion MQTT publish failed ({type(exc).__name__})",
                    extra={"event": "fusion_publish_failed"},
                )
        envelope = WebSocketEnvelope(channel=channel, data=payload)
        await self.websocket_hub.broadcast(envelope)

    def status(self, now: datetime | None = None) -> FusionStatusResponse:
        timestamp = now or datetime.now(UTC)
        with self._state_lock:
            activity = self._current_activity
            receipts = dict(self._last_receipt)
            source_updates = dict(self._last_source)
            database_healthy = self._database_healthy
            database_detail = self._database_detail
        modality_health = {
            modality: ModalityStatus(
                status=(
                    "online"
                    if receipt is not None
                    and (timestamp - receipt).total_seconds() <= self.settings.stale_timeout_seconds
                    else "offline"
                ),
                last_update=source_updates[modality],
            )
            for modality, receipt in receipts.items()
        }
        return FusionStatusResponse(
            activity=(activity.activity if activity else ActivityLabel.UNKNOWN),
            confidence=(activity.confidence if activity else 0.0),
            last_update=(activity.ts if activity else None),
            data_status=(
                "unavailable"
                if activity is None
                else "current"
                if (timestamp - activity.ts).total_seconds() <= self.settings.stale_timeout_seconds
                else "stale"
            ),
            modality_health=modality_health,
            components={
                "mqtt": ComponentStatus(
                    status="healthy" if self._connected.is_set() else "degraded",
                    detail="connected" if self._connected.is_set() else "disconnected",
                ),
                "database": ComponentStatus(
                    status="healthy" if database_healthy else "degraded",
                    detail=database_detail,
                ),
            },
        )

    def health(self) -> DependencyHealth:
        with self._state_lock:
            database_healthy = self._database_healthy
        healthy = self._connected.is_set() and database_healthy
        return DependencyHealth(
            status="healthy" if healthy else "degraded",
            detail=(
                "connected; persistence ready"
                if healthy
                else "MQTT disconnected or persistence retry pending"
            ),
        )

    async def stop(self) -> None:
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker
        client, self._client = self._client, None
        self._connected.clear()
        if client is not None:
            with suppress(Exception):
                client.disconnect()
            with suppress(Exception):
                client.loop_stop()
        await self.websocket_hub.close()

    def _set_database_health(self, healthy: bool, detail: str | None) -> None:
        with self._state_lock:
            self._database_healthy = healthy
            self._database_detail = detail

    def _record_database_failure(self, exc: Exception) -> None:
        self.counters["database_failures"] += 1
        self._set_database_health(False, f"database operation failed ({type(exc).__name__})")
        logger.error(
            f"Fusion database operation failed ({type(exc).__name__})",
            extra={"event": "fusion_database_failed"},
        )
