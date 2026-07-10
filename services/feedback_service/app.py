"""Milestone 1 FastAPI skeleton for the feedback service."""

from collections.abc import Sequence

from fastapi import FastAPI

from services.feedback_service.config import (
    SERVICE_NAME,
    SERVICE_TITLE,
    get_service_settings,
)
from services.runtime import (
    ManagedDependency,
    ServiceDefinition,
    create_service_app,
    database_dependency,
    mqtt_dependency,
)
from shared.config import Settings


def create_app(
    settings: Settings | None = None,
    dependencies: Sequence[ManagedDependency] | None = None,
) -> FastAPI:
    """Create the feedback API without invoking any LLM in Milestone 1."""

    resolved_settings = settings or get_service_settings()
    resolved_dependencies = (
        tuple(dependencies)
        if dependencies is not None
        else (
            mqtt_dependency(resolved_settings, SERVICE_NAME),
            database_dependency(resolved_settings),
        )
    )
    return create_service_app(
        ServiceDefinition(name=SERVICE_NAME, title=SERVICE_TITLE),
        resolved_settings,
        resolved_dependencies,
    )


app = create_app()
