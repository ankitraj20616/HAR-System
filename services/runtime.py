"""Shared FastAPI lifecycle and dependency health primitives.

This module intentionally contains infrastructure only. Activity recognition,
fusion, fall detection, and feedback generation belong to later milestones.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from threading import Event, Lock
from typing import Any, Literal, Protocol

from fastapi import FastAPI
from pydantic import BaseModel, Field

from shared.config import Settings
from shared.logging import configure_logging, get_logger

DependencyStatus = Literal["healthy", "degraded", "starting", "stopped"]


class DependencyHealth(BaseModel):
    """Public, secret-free state for one external dependency."""

    status: DependencyStatus
    detail: str | None = None


class HealthResponse(BaseModel):
    """Stable response contract shared by every backend service."""

    service: str
    version: str
    status: Literal["healthy", "degraded"]
    dependencies: dict[str, DependencyHealth] = Field(default_factory=dict)


class ManagedDependency(Protocol):
    """A connection managed by the FastAPI application lifespan."""

    name: str

    async def start(self) -> None:
        """Open the dependency connection or record a degraded state."""

    async def stop(self) -> None:
        """Close resources. Calling stop more than once must be safe."""

    def health(self) -> DependencyHealth:
        """Return the current dependency state without performing I/O."""


class _StatefulDependency:
    """Thread-safe state handling used by dependency callback threads."""

    name: str

    def __init__(self) -> None:
        self._state_lock = Lock()
        self._status: DependencyStatus = "starting"
        self._detail: str | None = None

    def _set_state(self, status: DependencyStatus, detail: str | None = None) -> None:
        with self._state_lock:
            self._status = status
            self._detail = detail

    def health(self) -> DependencyHealth:
        with self._state_lock:
            return DependencyHealth(status=self._status, detail=self._detail)


class MQTTDependency(_StatefulDependency):
    """Lifecycle wrapper around a paho MQTT client.

    The import is delayed until startup so importing the ASGI application never
    performs network I/O. Paho's background loop provides reconnect handling.
    """

    name = "mqtt"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        client_id: str,
        connect_timeout: float = 1.0,
    ) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._client_id = client_id
        self._connect_timeout = connect_timeout
        self._client: Any | None = None
        self._connected = Event()

    async def start(self) -> None:
        self._set_state("starting", "connecting to MQTT broker")
        self._connected.clear()
        try:
            await asyncio.to_thread(self._start_client)
            connected = await asyncio.to_thread(self._connected.wait, self._connect_timeout)
            if not connected:
                self._set_state(
                    "degraded",
                    "MQTT broker is unavailable; reconnecting in background",
                )
        except Exception as exc:  # dependency failures must not stop the API
            client, self._client = self._client, None
            if client is not None:
                with suppress(Exception):
                    await asyncio.to_thread(self._stop_client, client)
            self._set_state("degraded", _safe_failure("MQTT connection", exc))

    def _start_client(self) -> None:
        import paho.mqtt.client as mqtt

        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self._client_id,
                protocol=mqtt.MQTTv311,
            )
        except (AttributeError, TypeError):
            # paho-mqtt < 2.0 has no callback_api_version parameter.
            client = mqtt.Client(client_id=self._client_id, protocol=mqtt.MQTTv311)

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.connect_async(self._host, self._port, keepalive=60)
        self._client = client
        client.loop_start()

    def _on_connect(
        self,
        _client: Any,
        _userdata: Any,
        _flags: Any,
        reason: Any,
        *args: Any,
    ) -> None:
        reason_code = getattr(reason, "value", reason)
        if reason_code == 0:
            self._connected.set()
            self._set_state("healthy", "connected")
            return
        self._connected.clear()
        self._set_state("degraded", f"broker rejected connection (code {reason_code})")

    def _on_disconnect(self, _client: Any, _userdata: Any, *args: Any) -> None:
        self._connected.clear()
        self._set_state("degraded", "MQTT connection lost; reconnecting")

    async def stop(self) -> None:
        client, self._client = self._client, None
        self._connected.clear()
        try:
            if client is not None:
                await asyncio.to_thread(self._stop_client, client)
        finally:
            self._set_state("stopped", "connection closed")

    @staticmethod
    def _stop_client(client: Any) -> None:
        try:
            client.disconnect()
        finally:
            client.loop_stop()


class DatabaseDependency(_StatefulDependency):
    """Own one PostgreSQL connection for readiness and later repositories."""

    name = "database"

    def __init__(
        self,
        *,
        database_url: str,
        connector: Callable[..., Any] | None = None,
        connect_timeout: int = 1,
    ) -> None:
        super().__init__()
        self._database_url = database_url
        self._connector = connector
        self._connect_timeout = connect_timeout
        self._connection: Any | None = None

    @property
    def connection(self) -> Any | None:
        """Expose the managed connection for later repository wiring."""

        return self._connection

    async def start(self) -> None:
        self._set_state("starting", "connecting to PostgreSQL")
        try:
            self._connection = await asyncio.to_thread(self._open_and_check)
            self._set_state("healthy", "connected")
        except Exception as exc:  # dependency failures must not stop the API
            self._connection = None
            self._set_state("degraded", _safe_failure("database connection", exc))

    def _open_and_check(self) -> Any:
        connector = self._connector
        if connector is None:
            import psycopg

            connector = psycopg.connect

        database_url = self._database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        connection = connector(
            database_url,
            connect_timeout=self._connect_timeout,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            connection.close()
            raise
        return connection

    async def stop(self) -> None:
        connection, self._connection = self._connection, None
        try:
            if connection is not None:
                await asyncio.to_thread(connection.close)
        finally:
            self._set_state("stopped", "connection closed")


@dataclass(frozen=True)
class ServiceDefinition:
    """Static metadata for a service skeleton."""

    name: str
    title: str


def create_service_app(
    definition: ServiceDefinition,
    settings: Settings,
    dependencies: Sequence[ManagedDependency],
) -> FastAPI:
    """Build a FastAPI service with health, logs, and safe lifecycle handling."""

    configure_logging(definition.name, level=settings.log_level)
    logger = get_logger(__name__)
    managed_dependencies = tuple(dependencies)
    dependency_names = [dependency.name for dependency in managed_dependencies]
    if len(dependency_names) != len(set(dependency_names)):
        raise ValueError("dependency names must be unique within a service")

    startup_failures: dict[str, DependencyHealth] = {}

    def dependency_health(dependency: ManagedDependency) -> DependencyHealth:
        startup_failure = startup_failures.get(dependency.name)
        if startup_failure is not None:
            return startup_failure
        try:
            return dependency.health()
        except Exception as exc:
            return DependencyHealth(
                status="degraded",
                detail=_safe_failure(f"{dependency.name} health check", exc),
            )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = settings
        application.state.dependencies = {
            dependency.name: dependency for dependency in managed_dependencies
        }
        try:
            logger.info(
                "Service startup started",
                extra={"event": "service_starting", "service": definition.name},
            )
            startup_failures.clear()
            for dependency in managed_dependencies:
                try:
                    await dependency.start()
                except Exception as exc:
                    startup_failures[dependency.name] = DependencyHealth(
                        status="degraded",
                        detail=_safe_failure(f"{dependency.name} startup", exc),
                    )
                state = dependency_health(dependency)
                log = logger.info if state.status == "healthy" else logger.warning
                log(
                    f"Dependency {dependency.name} is {state.status}",
                    extra={
                        "event": "dependency_state",
                        "service": definition.name,
                        "dependency": dependency.name,
                        "dependency_status": state.status,
                    },
                )
            logger.info(
                "Service startup completed",
                extra={"event": "service_started", "service": definition.name},
            )
            yield
        finally:
            logger.info(
                "Service shutdown started",
                extra={"event": "service_stopping", "service": definition.name},
            )
            for dependency in reversed(managed_dependencies):
                try:
                    await dependency.stop()
                except Exception as exc:  # make best effort to close every resource
                    logger.error(
                        f"Could not close dependency {dependency.name}: {type(exc).__name__}",
                        extra={
                            "event": "dependency_shutdown_failed",
                            "service": definition.name,
                            "dependency": dependency.name,
                        },
                    )
            logger.info(
                "Service shutdown completed",
                extra={"event": "service_stopped", "service": definition.name},
            )

    application = FastAPI(
        title=definition.title,
        version=settings.service_version,
        lifespan=lifespan,
    )

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        dependency_states = {
            dependency.name: dependency_health(dependency) for dependency in managed_dependencies
        }
        overall_status: Literal["healthy", "degraded"] = (
            "healthy"
            if all(state.status == "healthy" for state in dependency_states.values())
            else "degraded"
        )
        return HealthResponse(
            service=definition.name,
            version=settings.service_version,
            status=overall_status,
            dependencies=dependency_states,
        )

    return application


def mqtt_dependency(settings: Settings, service_name: str) -> MQTTDependency:
    """Create a stable-ID MQTT dependency from shared settings."""

    return MQTTDependency(
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        client_id=f"har-{service_name}",
    )


def database_dependency(settings: Settings) -> DatabaseDependency:
    """Create a PostgreSQL dependency from shared settings."""

    return DatabaseDependency(database_url=settings.database_url)


def _safe_failure(operation: str, exc: Exception) -> str:
    """Describe a failure without echoing URLs, credentials, or payloads."""

    return f"{operation} failed ({type(exc).__name__})"
