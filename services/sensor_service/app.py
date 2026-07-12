"""FastAPI entry point and MQTT-backed sensor recognition runtime."""

from collections.abc import Sequence

from fastapi import FastAPI

from services.runtime import ManagedDependency, ServiceDefinition, create_service_app
from services.sensor_service.config import (
    SERVICE_NAME,
    SERVICE_TITLE,
    SensorSettings,
    get_service_settings,
)
from services.sensor_service.mqtt import SensorMQTTDependency
from shared.config import Settings


def create_app(
    settings: Settings | None = None,
    dependencies: Sequence[ManagedDependency] | None = None,
) -> FastAPI:
    """Create the sensor API; network/model work begins only during lifespan startup."""

    resolved_settings = settings or get_service_settings()
    if dependencies is not None:
        resolved_dependencies = tuple(dependencies)
    else:
        sensor_settings = (
            resolved_settings
            if isinstance(resolved_settings, SensorSettings)
            else SensorSettings(**resolved_settings.model_dump())
        )
        resolved_dependencies = (SensorMQTTDependency(sensor_settings),)
    return create_service_app(
        ServiceDefinition(name=SERVICE_NAME, title=SERVICE_TITLE),
        resolved_settings,
        resolved_dependencies,
    )


app = create_app()
