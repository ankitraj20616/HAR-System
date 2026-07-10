"""Canonical labels used across every HAR component.

Incoming dataset/model labels should be passed through :func:`map_activity_label`.
Wire contracts remain strict and reject invented labels.
"""

from enum import Enum
from typing import Final


class StringEnum(str, Enum):
    """A JSON-friendly enum with readable string conversion."""

    def __str__(self) -> str:
        return self.value


class ActivityLabel(StringEnum):
    WALKING = "WALKING"
    SITTING = "SITTING"
    STANDING = "STANDING"
    LYING = "LYING"
    EXERCISING = "EXERCISING"
    UNKNOWN = "UNKNOWN"


class EventType(StringEnum):
    FALL = "FALL"
    INACTIVITY = "INACTIVITY"
    ABNORMAL_PATTERN = "ABNORMAL_PATTERN"


class EventSeverity(StringEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Modality(StringEnum):
    SENSOR = "sensor"
    VIDEO = "video"


class Orientation(StringEnum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    UNKNOWN = "unknown"


class FeedbackMode(StringEnum):
    ALERT = "alert"
    FEEDBACK = "feedback"
    SUMMARY = "summary"


CANONICAL_ACTIVITIES: Final[tuple[str, ...]] = tuple(item.value for item in ActivityLabel)
CANONICAL_EVENTS: Final[tuple[str, ...]] = tuple(item.value for item in EventType)

# Dataset/model outputs are normalized here, never inside individual services.
_ACTIVITY_ALIASES: Final[dict[str, ActivityLabel]] = {
    "WALK": ActivityLabel.WALKING,
    "UPSTAIRS": ActivityLabel.WALKING,
    "DOWNSTAIRS": ActivityLabel.WALKING,
    "WALKING_UPSTAIRS": ActivityLabel.WALKING,
    "WALKING_DOWNSTAIRS": ActivityLabel.WALKING,
    "STAIRS": ActivityLabel.WALKING,
    "JOGGING": ActivityLabel.EXERCISING,
    "RUNNING": ActivityLabel.EXERCISING,
    "BIKING": ActivityLabel.EXERCISING,
    "BICYCLING": ActivityLabel.EXERCISING,
    "LAYING": ActivityLabel.LYING,
    "LAYING_DOWN": ActivityLabel.LYING,
    "LIE": ActivityLabel.LYING,
    "SIT": ActivityLabel.SITTING,
    "STAND": ActivityLabel.STANDING,
}


def map_activity_label(value: object) -> ActivityLabel:
    """Map an external label to the project vocabulary.

    Unrecognized, empty, or non-string inputs become ``UNKNOWN``. This helper is
    intended for model/dataset boundaries; Pydantic message schemas stay strict.
    """

    if isinstance(value, ActivityLabel):
        return value
    if not isinstance(value, str) or not value.strip():
        return ActivityLabel.UNKNOWN
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    try:
        return ActivityLabel(normalized)
    except ValueError:
        return _ACTIVITY_ALIASES.get(normalized, ActivityLabel.UNKNOWN)
