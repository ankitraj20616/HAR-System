"""FastAPI entry point for the Milestone 2 video recognition pipeline."""

from collections.abc import Sequence

from fastapi import FastAPI

from services.runtime import (
    ManagedDependency,
    ServiceDefinition,
    create_service_app,
)
from services.video_service.adapters import (
    MediaPipePoseEstimator,
    OpenCVCamera,
    VideoMQTTPublisher,
)
from services.video_service.config import (
    SERVICE_NAME,
    SERVICE_TITLE,
    VideoSettings,
    get_service_settings,
)
from services.video_service.pipeline import VideoPipeline
from shared.config import Settings


def create_app(
    settings: Settings | None = None,
    dependencies: Sequence[ManagedDependency] | None = None,
) -> FastAPI:
    """Create the video API without opening a camera in Milestone 1."""

    resolved_settings = settings or get_service_settings()
    if dependencies is not None:
        resolved_dependencies = tuple(dependencies)
    else:
        video_settings = (
            resolved_settings
            if isinstance(resolved_settings, VideoSettings)
            else VideoSettings.model_validate(resolved_settings.model_dump())
        )
        publisher = VideoMQTTPublisher(
            host=video_settings.mqtt_host,
            port=video_settings.mqtt_port,
            client_id=f"har-{SERVICE_NAME}",
        )
        pipeline = VideoPipeline(
            video_settings,
            publisher,
            camera_factory=lambda: OpenCVCamera(video_settings.camera_index, video_settings.fps),
            estimator_factory=lambda: MediaPipePoseEstimator(video_settings.min_visibility),
        )
        resolved_dependencies = (publisher, pipeline)
    return create_service_app(
        ServiceDefinition(name=SERVICE_NAME, title=SERVICE_TITLE),
        resolved_settings,
        resolved_dependencies,
    )


app = create_app()
