"""Milestone 1 FastAPI skeleton for the sensor service."""

from collections.abc import Sequence

from fastapi import FastAPI

from services.runtime import (
    ManagedDependency,
    ServiceDefinition,
    create_service_app,
    mqtt_dependency,
)
from services.sensor_service.config import (
    SERVICE_NAME,
    SERVICE_TITLE,
    get_service_settings,
)
from shared.config import Settings


def create_app(
    settings: Settings | None = None,
    dependencies: Sequence[ManagedDependency] | None = None,
) -> FastAPI:
    """Create the sensor API without starting business processing loops."""

    resolved_settings = settings or get_service_settings()
    resolved_dependencies = (
        tuple(dependencies)
        if dependencies is not None
        else (mqtt_dependency(resolved_settings, SERVICE_NAME),)
    )
    return create_service_app(
        ServiceDefinition(name=SERVICE_NAME, title=SERVICE_TITLE),
        resolved_settings,
        resolved_dependencies,
    )


app = create_app()
