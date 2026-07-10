"""Integration-level contract tests for all service health endpoints."""

import asyncio
from dataclasses import dataclass

import httpx
import pytest
from fastapi import FastAPI

from services.feedback_service.app import create_app as create_feedback_app
from services.fusion_service.app import create_app as create_fusion_app
from services.runtime import DependencyHealth
from services.sensor_service.app import create_app as create_sensor_app
from services.video_service.app import create_app as create_video_app
from shared.config import Settings


@dataclass
class FakeDependency:
    name: str
    status: str = "healthy"
    fail_start: bool = False
    fail_stop: bool = False
    fail_health: bool = False
    started: bool = False
    stopped: bool = False

    async def start(self) -> None:
        self.started = True
        if self.fail_start:
            raise ConnectionError("secret connection details")

    async def stop(self) -> None:
        self.stopped = True
        if self.fail_stop:
            raise RuntimeError("close failed")

    def health(self) -> DependencyHealth:
        if self.fail_health:
            raise RuntimeError("health failed")
        return DependencyHealth(status=self.status, detail="test dependency")


async def get_health(app: FastAPI) -> httpx.Response:
    """Call the ASGI app while explicitly owning its lifespan.

    This avoids TestClient's blocking portal and makes startup/shutdown ordering
    explicit in the integration contract.
    """

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/health")


@pytest.mark.parametrize(
    ("factory", "service_name", "dependency_names"),
    [
        (create_sensor_app, "sensor_service", ("mqtt",)),
        (create_video_app, "video_service", ("mqtt",)),
        (create_fusion_app, "fusion_service", ("mqtt", "database")),
        (create_feedback_app, "feedback_service", ("mqtt", "database")),
    ],
)
def test_health_endpoint_reports_service_and_dependencies(
    factory, service_name: str, dependency_names: tuple[str, ...]
) -> None:
    settings = Settings(service_version="0.1.0")
    dependencies = [FakeDependency(name=name) for name in dependency_names]

    response = asyncio.run(get_health(factory(settings=settings, dependencies=dependencies)))

    assert response.status_code == 200
    assert response.json() == {
        "service": service_name,
        "version": "0.1.0",
        "status": "healthy",
        "dependencies": {
            name: {"status": "healthy", "detail": "test dependency"} for name in dependency_names
        },
    }
    assert all(dependency.started for dependency in dependencies)
    assert all(dependency.stopped for dependency in dependencies)


def test_dependency_failure_degrades_health_without_crashing_api() -> None:
    mqtt = FakeDependency(name="mqtt", status="healthy")
    database = FakeDependency(name="database", status="degraded")
    app = create_fusion_app(
        settings=Settings(service_version="0.1.0"),
        dependencies=(mqtt, database),
    )

    response = asyncio.run(get_health(app))

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["database"]["status"] == "degraded"
    assert mqtt.stopped is True
    assert database.stopped is True


def test_unhandled_dependency_start_failure_is_reported_and_cleanup_continues() -> None:
    mqtt = FakeDependency(name="mqtt", fail_start=True)
    database = FakeDependency(name="database", fail_stop=True)
    app = create_fusion_app(
        settings=Settings(service_version="0.1.0"),
        dependencies=(mqtt, database),
    )

    response = asyncio.run(get_health(app))

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["mqtt"] == {
        "status": "degraded",
        "detail": "mqtt startup failed (ConnectionError)",
    }
    assert mqtt.started is True
    assert database.started is True
    assert mqtt.stopped is True
    assert database.stopped is True


def test_health_callback_failure_is_reported_without_exposing_exception_text() -> None:
    dependency = FakeDependency(name="mqtt", fail_health=True)
    app = create_sensor_app(
        settings=Settings(service_version="0.1.0"),
        dependencies=(dependency,),
    )

    response = asyncio.run(get_health(app))

    assert response.status_code == 200
    assert response.json()["dependencies"]["mqtt"] == {
        "status": "degraded",
        "detail": "mqtt health check failed (RuntimeError)",
    }


def test_duplicate_dependency_names_are_rejected() -> None:
    dependencies = (FakeDependency(name="mqtt"), FakeDependency(name="mqtt"))

    with pytest.raises(ValueError, match="dependency names must be unique"):
        create_sensor_app(settings=Settings(), dependencies=dependencies)
