"""FastAPI entry point for the Fusion, safety, and history service."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI

from services.fusion_service.api import create_router
from services.fusion_service.config import (
    SERVICE_NAME,
    SERVICE_TITLE,
    FusionSettings,
    get_service_settings,
)
from services.fusion_service.runtime import FusionMQTTDependency
from services.runtime import (
    ManagedDependency,
    ServiceDefinition,
    create_service_app,
    database_dependency,
)
from shared.config import Settings
from shared.db import ActivityRepository, EventRepository


def create_app(
    settings: Settings | None = None,
    dependencies: Sequence[ManagedDependency] | None = None,
    *,
    runtime: FusionMQTTDependency | None = None,
    fusion_runtime: FusionMQTTDependency | None = None,
    activity_repository: ActivityRepository | None = None,
    event_repository: EventRepository | None = None,
) -> FastAPI:
    """Create the Fusion API with injectable transport and repositories."""

    base_settings = settings or get_service_settings()
    resolved_settings = (
        base_settings
        if isinstance(base_settings, FusionSettings)
        else FusionSettings.model_validate(base_settings.model_dump())
    )
    if runtime is not None and fusion_runtime is not None:
        raise ValueError("pass only one of runtime or fusion_runtime")
    controller = (
        runtime
        or fusion_runtime
        or FusionMQTTDependency(
            resolved_settings,
            activity_repository=activity_repository,
            event_repository=event_repository,
        )
    )
    if dependencies is not None:
        resolved_dependencies = tuple(dependencies)
    else:
        # Database readiness is exposed separately; the MQTT dependency also
        # runs the repeatable M3 schema migration before consuming messages.
        resolved_dependencies = (
            database_dependency(resolved_settings),
            controller,
        )
    application = create_service_app(
        ServiceDefinition(name=SERVICE_NAME, title=SERVICE_TITLE),
        resolved_settings,
        resolved_dependencies,
    )
    application.include_router(create_router(controller))
    return application


app = create_app()
