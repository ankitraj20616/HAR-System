"""FastAPI entry point for structured feedback generation and alert text."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI

from services.feedback_service.api import create_router
from services.feedback_service.config import (
    SERVICE_NAME,
    SERVICE_TITLE,
    FeedbackSettings,
    get_service_settings,
)
from services.feedback_service.llm import FeedbackProvider
from services.feedback_service.runtime import FeedbackRuntime
from services.runtime import (
    ManagedDependency,
    ServiceDefinition,
    create_service_app,
    database_dependency,
)
from shared.config import Settings
from shared.db import ActivityRepository, EventRepository, FeedbackRepository


def create_app(
    settings: Settings | None = None,
    dependencies: Sequence[ManagedDependency] | None = None,
    *,
    runtime: FeedbackRuntime | None = None,
    provider: FeedbackProvider | None = None,
    activity_repository: ActivityRepository | None = None,
    event_repository: EventRepository | None = None,
    feedback_repository: FeedbackRepository | None = None,
) -> FastAPI:
    base_settings = settings or get_service_settings()
    resolved_settings = (
        base_settings
        if isinstance(base_settings, FeedbackSettings)
        else FeedbackSettings.model_validate(base_settings.model_dump())
    )
    controller = runtime or FeedbackRuntime(
        resolved_settings,
        provider=provider,
        activity_repository=activity_repository,
        event_repository=event_repository,
        feedback_repository=feedback_repository,
    )
    resolved_dependencies = (
        tuple(dependencies)
        if dependencies is not None
        else (database_dependency(resolved_settings), controller)
    )
    application = create_service_app(
        ServiceDefinition(name=SERVICE_NAME, title=SERVICE_TITLE),
        resolved_settings,
        resolved_dependencies,
    )
    application.include_router(create_router(controller))
    application.state.feedback_runtime = controller
    return application


app = create_app()
