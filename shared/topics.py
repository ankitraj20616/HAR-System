"""MQTT topic names and delivery policy."""

from dataclasses import dataclass
from typing import Final

SENSOR_RAW: Final = "har/sensor/raw"
SENSOR_PREDICTION: Final = "har/sensor/prediction"
VIDEO_PREDICTION: Final = "har/video/prediction"
ACTIVITY: Final = "har/activity"
EVENT: Final = "har/event"
FEEDBACK: Final = "har/feedback"

ALL_TOPICS: Final = frozenset(
    {SENSOR_RAW, SENSOR_PREDICTION, VIDEO_PREDICTION, ACTIVITY, EVENT, FEEDBACK}
)


@dataclass(frozen=True)
class TopicPolicy:
    topic: str
    qos: int
    retain: bool = False


# Predictions and safety events use at-least-once delivery. Raw windows can be
# regenerated and avoid broker pressure with QoS 0.
POLICIES: Final = {
    SENSOR_RAW: TopicPolicy(SENSOR_RAW, qos=0),
    SENSOR_PREDICTION: TopicPolicy(SENSOR_PREDICTION, qos=1),
    VIDEO_PREDICTION: TopicPolicy(VIDEO_PREDICTION, qos=1),
    ACTIVITY: TopicPolicy(ACTIVITY, qos=1),
    EVENT: TopicPolicy(EVENT, qos=1),
    FEEDBACK: TopicPolicy(FEEDBACK, qos=1),
}


def policy_for(topic: str) -> TopicPolicy:
    """Return the agreed delivery policy or fail loudly for an unknown topic."""

    try:
        return POLICIES[topic]
    except KeyError as exc:
        raise ValueError(f"Unknown HAR MQTT topic: {topic!r}") from exc
