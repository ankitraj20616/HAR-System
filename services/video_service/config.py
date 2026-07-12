"""Validated configuration for the privacy-preserving video pipeline."""

from pydantic import Field, model_validator

from shared.config import Settings

SERVICE_NAME = "video_service"
SERVICE_TITLE = "HAR Video Service"


class VideoSettings(Settings):
    """Video-specific settings, all overridable through environment variables."""

    camera_index: int = Field(default=0, ge=0)
    fps: float = Field(default=12.0, ge=1.0, le=60.0)
    min_visibility: float = Field(default=0.6, ge=0.0, le=1.0)
    horizontal_angle_threshold: float = Field(default=25.0, gt=0.0, lt=45.0)
    sitting_joint_angle: float = Field(default=135.0, ge=70.0, le=150.0)
    standing_joint_angle: float = Field(default=155.0, ge=120.0, le=179.0)
    motion_history_length: int = Field(default=12, ge=3, le=120)
    walking_motion_threshold: float = Field(default=0.018, gt=0.0, le=0.5)
    exercise_motion_threshold: float = Field(default=0.045, gt=0.0, le=1.0)
    reconnect_attempts: int = Field(default=5, ge=1, le=100)
    reconnect_initial_backoff: float = Field(default=0.25, ge=0.0, le=30.0)
    reconnect_max_backoff: float = Field(default=5.0, gt=0.0, le=60.0)

    @model_validator(mode="after")
    def coherent_thresholds(self) -> "VideoSettings":
        if self.sitting_joint_angle >= self.standing_joint_angle:
            raise ValueError("SITTING_JOINT_ANGLE must be below STANDING_JOINT_ANGLE")
        if self.walking_motion_threshold >= self.exercise_motion_threshold:
            raise ValueError("WALKING_MOTION_THRESHOLD must be below EXERCISE_MOTION_THRESHOLD")
        if self.reconnect_initial_backoff > self.reconnect_max_backoff:
            raise ValueError("RECONNECT_INITIAL_BACKOFF must not exceed RECONNECT_MAX_BACKOFF")
        return self


def get_service_settings() -> VideoSettings:
    """Build one fully environment-driven settings object for this service."""

    return VideoSettings()
