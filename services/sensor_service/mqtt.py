"""MQTT transport for the sensor pipeline."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from threading import Event, Lock
from typing import Any

from services.runtime import DependencyHealth
from shared.logging import get_logger
from shared.topics import SENSOR_PREDICTION, SENSOR_RAW, policy_for

from .config import SensorSettings
from .pipeline import InvalidSensorPayload, SensorPipeline

logger = get_logger(__name__)


class SensorMQTTDependency:
    """Own MQTT subscription/publishing and expose combined transport/model health."""

    name = "mqtt"

    def __init__(
        self,
        settings: SensorSettings,
        pipeline: SensorPipeline | None = None,
        client_factory: Any | None = None,
        connect_timeout: float = 1.0,
    ) -> None:
        self.settings = settings
        self.pipeline = pipeline or SensorPipeline(settings)
        self._client_factory = client_factory
        self._connect_timeout = connect_timeout
        self._client: Any | None = None
        self._connected = Event()
        self._lock = Lock()
        self._transport_detail = "not started"

    async def start(self) -> None:
        self.pipeline.start()
        self._connected.clear()
        try:
            await asyncio.to_thread(self._start_client)
            connected = await asyncio.to_thread(self._connected.wait, self._connect_timeout)
            if not connected:
                self._set_transport("MQTT broker unavailable; reconnecting")
        except Exception as exc:
            self._set_transport(f"MQTT startup failed ({type(exc).__name__})")

    def _start_client(self) -> None:
        if self._client_factory is None:
            import paho.mqtt.client as mqtt

            try:
                client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id="har-sensor_service",
                    protocol=mqtt.MQTTv311,
                )
            except (AttributeError, TypeError):
                client = mqtt.Client(client_id="har-sensor_service", protocol=mqtt.MQTTv311)
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
            self._set_transport(f"broker rejected connection (code {reason_code})")
            return
        raw_policy = policy_for(SENSOR_RAW)
        client.subscribe(raw_policy.topic, qos=raw_policy.qos)
        self._connected.set()
        self._set_transport("connected and subscribed")

    def _on_disconnect(self, _client: Any, _userdata: Any, *args: Any) -> None:
        self._connected.clear()
        self._set_transport("MQTT connection lost; reconnecting")

    def _on_message(self, client: Any, _userdata: Any, message: Any) -> None:
        if message.topic != SENSOR_RAW:
            return
        try:
            predictions = self.pipeline.process_json(message.payload)
            policy = policy_for(SENSOR_PREDICTION)
            for prediction in predictions:
                client.publish(
                    policy.topic,
                    prediction.model_dump_json(),
                    qos=policy.qos,
                    retain=policy.retain,
                )
        except InvalidSensorPayload as exc:
            logger.warning(str(exc), extra={"event": "sensor_payload_rejected"})
        except Exception as exc:
            logger.error(
                f"sensor payload processing failed ({type(exc).__name__})",
                extra={"event": "sensor_processing_failed"},
            )

    def health(self) -> DependencyHealth:
        pipeline_health = self.pipeline.health
        with self._lock:
            transport_detail = self._transport_detail
        connected = self._connected.is_set()
        degraded = not connected or pipeline_health.degraded
        detail = transport_detail
        if pipeline_health.degraded:
            detail = f"{detail}; {pipeline_health.detail}"
        return DependencyHealth(status="degraded" if degraded else "healthy", detail=detail)

    async def stop(self) -> None:
        client, self._client = self._client, None
        self._connected.clear()
        if client is not None:
            with suppress(Exception):
                client.disconnect()
            with suppress(Exception):
                client.loop_stop()
        self._set_transport("connection closed")

    def _set_transport(self, detail: str) -> None:
        with self._lock:
            self._transport_detail = detail
