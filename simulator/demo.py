"""Offline, dependency-free IMU publisher for the one-command demo stack.

This source is intentionally synthetic and is not part of the evaluation data. Public dataset
replay remains available through :mod:`simulator.replay`; this process only makes a clean checkout
demonstrable without downloading a dataset at runtime.
"""

from __future__ import annotations

import math
import signal
import time
from datetime import UTC, datetime
from threading import Event
from typing import Any

import paho.mqtt.client as mqtt
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.logging import configure_logging
from shared.schemas import SensorRaw, SensorWindow
from shared.topics import SENSOR_RAW, policy_for


class DemoSettings(BaseSettings):
    """Validated environment contract for the Compose demo publisher."""

    mqtt_host: str = Field(default="localhost", min_length=1)
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    simulator_device_id: str = Field(default="demo-sim-01", min_length=1, max_length=128)
    simulator_sampling_hz: float = Field(default=50.0, ge=10.0, le=200.0)
    simulator_chunk_seconds: float = Field(default=0.5, ge=0.1, le=5.0)
    simulator_scenario_seconds: float = Field(default=12.0, ge=2.0, le=300.0)

    @model_validator(mode="after")
    def chunk_contains_samples(self) -> DemoSettings:
        if self.simulator_sampling_hz * self.simulator_chunk_seconds < 1:
            raise ValueError("SIMULATOR_CHUNK_SECONDS must contain at least one sample")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )


def generate_chunk(
    *, sampling_hz: float, chunk_seconds: float, elapsed_seconds: float, scenario_seconds: float
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    """Return deterministic standing/walking/exercise-like samples in g and rad/s."""

    count = max(1, round(sampling_hz * chunk_seconds))
    phase = int(elapsed_seconds / scenario_seconds) % 3
    accel: list[tuple[float, float, float]] = []
    gyro: list[tuple[float, float, float]] = []
    for index in range(count):
        t = elapsed_seconds + index / sampling_hz
        if phase == 0:  # quiet upright period
            accel.append((0.006 * math.sin(t), 0.004 * math.cos(t), 1.0))
            gyro.append((0.002, 0.001, 0.002))
        elif phase == 1:  # rhythmic walking-like motion
            wave = math.sin(2.0 * math.pi * 1.8 * t)
            accel.append((0.18 * wave, 0.08 * math.cos(2.0 * math.pi * 1.8 * t), 1.0 + 0.12 * wave))
            gyro.append((0.18 * wave, 0.10 * math.cos(2.0 * math.pi * 1.8 * t), 0.05))
        else:  # vigorous movement, bounded well below implausible sensor values
            wave = math.sin(2.0 * math.pi * 3.0 * t)
            accel.append((0.55 * wave, 0.35 * math.cos(2.0 * math.pi * 2.5 * t), 1.0 + 0.4 * wave))
            gyro.append((1.2 * wave, 1.0 * math.cos(2.0 * math.pi * 2.5 * t), 0.6 * wave))
    return accel, gyro


def _mqtt_client(settings: DemoSettings, connected: Event, logger: Any) -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"har-{settings.simulator_device_id}",
        protocol=mqtt.MQTTv311,
    )

    def on_connect(_client: mqtt.Client, _userdata: Any, _flags: Any, reason: Any, *_: Any) -> None:
        reason_code = getattr(reason, "value", reason)
        if reason_code == 0:
            connected.set()
            logger.info("demo simulator connected", extra={"event": "simulator_connected"})
        else:
            connected.clear()
            logger.warning(
                "demo simulator connection rejected",
                extra={"event": "simulator_connect_rejected", "reason_code": reason_code},
            )

    def on_disconnect(_client: mqtt.Client, _userdata: Any, *_: Any) -> None:
        connected.clear()
        logger.warning(
            "demo simulator disconnected; reconnecting",
            extra={"event": "simulator_disconnected"},
        )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.max_queued_messages_set(100)
    return client


def main() -> int:
    settings = DemoSettings()
    logger = configure_logging("simulator-demo")
    stopping = Event()
    connected = Event()
    client = _mqtt_client(settings, connected, logger)

    def stop(_signum: int, _frame: object) -> None:
        stopping.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()
    started = time.monotonic()
    next_publish = started
    policy = policy_for(SENSOR_RAW)
    try:
        while not stopping.is_set():
            now = time.monotonic()
            if now < next_publish:
                stopping.wait(min(next_publish - now, 0.1))
                continue
            elapsed = now - started
            accel, gyro = generate_chunk(
                sampling_hz=settings.simulator_sampling_hz,
                chunk_seconds=settings.simulator_chunk_seconds,
                elapsed_seconds=elapsed,
                scenario_seconds=settings.simulator_scenario_seconds,
            )
            if connected.is_set():
                payload = SensorRaw(
                    ts=datetime.now(UTC),
                    device_id=settings.simulator_device_id,
                    sampling_hz=settings.simulator_sampling_hz,
                    window=SensorWindow(accel=accel, gyro=gyro),
                )
                client.publish(
                    policy.topic,
                    payload.model_dump_json(),
                    qos=policy.qos,
                    retain=policy.retain,
                )
            next_publish += settings.simulator_chunk_seconds
            if next_publish < now - settings.simulator_chunk_seconds:
                next_publish = now + settings.simulator_chunk_seconds
    finally:
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
