"""Deterministic geometric and temporal video activity classification."""

from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass

from services.video_service.config import VideoSettings
from services.video_service.landmarks import (
    PoseLandmarks,
    midpoint,
    three_point_angle,
)
from shared.labels import ActivityLabel, Orientation

LEFT_SHOULDER = "left_shoulder"
RIGHT_SHOULDER = "right_shoulder"
LEFT_HIP = "left_hip"
RIGHT_HIP = "right_hip"
LEFT_KNEE = "left_knee"
RIGHT_KNEE = "right_knee"
LEFT_ANKLE = "left_ankle"
RIGHT_ANKLE = "right_ankle"
LEFT_WRIST = "left_wrist"
RIGHT_WRIST = "right_wrist"

ESSENTIAL = (
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
)
MOTION_POINTS = ESSENTIAL + (LEFT_WRIST, RIGHT_WRIST)


@dataclass(frozen=True, slots=True)
class PoseFeatures:
    torso_angle_from_vertical: float
    left_hip_angle: float
    right_hip_angle: float
    left_knee_angle: float
    right_knee_angle: float
    normalized_body_height: float
    mean_visibility: float
    hip_center_x: float
    ankle_offset: float
    movement_signal: float
    coordinates: tuple[tuple[str, float, float], ...]

    @property
    def mean_hip_angle(self) -> float:
        return (self.left_hip_angle + self.right_hip_angle) / 2.0

    @property
    def mean_knee_angle(self) -> float:
        return (self.left_knee_angle + self.right_knee_angle) / 2.0


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    label: ActivityLabel
    confidence: float
    orientation: Orientation
    features: PoseFeatures | None = None


def extract_features(pose: PoseLandmarks, min_visibility: float) -> PoseFeatures | None:
    """Derive privacy-safe numeric features, or ``None`` for incomplete poses."""

    points = pose.require(ESSENTIAL, min_visibility)
    if points is None:
        return None
    named = dict(zip(ESSENTIAL, points, strict=True))
    shoulder_center = midpoint(named[LEFT_SHOULDER], named[RIGHT_SHOULDER])
    hip_center = midpoint(named[LEFT_HIP], named[RIGHT_HIP])
    torso_dx = shoulder_center.x - hip_center.x
    torso_dy = shoulder_center.y - hip_center.y
    if math.hypot(torso_dx, torso_dy) <= 1e-12:
        return None
    torso_angle = math.degrees(math.atan2(abs(torso_dx), abs(torso_dy)))

    try:
        left_hip_angle = three_point_angle(named[LEFT_SHOULDER], named[LEFT_HIP], named[LEFT_KNEE])
        right_hip_angle = three_point_angle(
            named[RIGHT_SHOULDER], named[RIGHT_HIP], named[RIGHT_KNEE]
        )
        left_knee_angle = three_point_angle(named[LEFT_HIP], named[LEFT_KNEE], named[LEFT_ANKLE])
        right_knee_angle = three_point_angle(
            named[RIGHT_HIP], named[RIGHT_KNEE], named[RIGHT_ANKLE]
        )
    except ValueError:
        return None

    visible = pose.visible(min_visibility)
    ys = [point.y for point in visible.values()]
    coordinates = tuple(
        sorted((name, point.x, point.y) for name, point in visible.items() if name in MOTION_POINTS)
    )
    wrists = [visible[name].y for name in (LEFT_WRIST, RIGHT_WRIST) if name in visible]
    return PoseFeatures(
        torso_angle_from_vertical=torso_angle,
        left_hip_angle=left_hip_angle,
        right_hip_angle=right_hip_angle,
        left_knee_angle=left_knee_angle,
        right_knee_angle=right_knee_angle,
        normalized_body_height=max(ys) - min(ys),
        mean_visibility=sum(point.visibility for point in points) / len(points),
        hip_center_x=hip_center.x,
        ankle_offset=named[LEFT_ANKLE].y - named[RIGHT_ANKLE].y,
        movement_signal=sum(wrists) / len(wrists) if wrists else shoulder_center.y,
        coordinates=coordinates,
    )


class ActivityClassifier:
    """Stateful classifier: posture is geometric, movement needs short history."""

    def __init__(self, settings: VideoSettings) -> None:
        self.settings = settings
        self._history: deque[PoseFeatures] = deque(maxlen=settings.motion_history_length)
        self._labels: deque[ActivityLabel] = deque(maxlen=settings.motion_history_length)

    def classify(self, pose: PoseLandmarks | None) -> ClassificationResult:
        if pose is None:
            return self._unknown()
        features = extract_features(pose, self.settings.min_visibility)
        if features is None:
            return self._unknown()

        orientation = self._orientation(features.torso_angle_from_vertical)
        upright = features.torso_angle_from_vertical <= self.settings.horizontal_angle_threshold
        self._history.append(features)
        motion, alternations, repetitive = self._temporal_metrics()

        if orientation is Orientation.HORIZONTAL:
            label = ActivityLabel.LYING
            margin = self._horizontal_margin(features.torso_angle_from_vertical)
        elif (
            self._history_ready()
            and upright
            and repetitive
            and motion >= self.settings.exercise_motion_threshold
        ):
            label = ActivityLabel.EXERCISING
            margin = self._above_margin(motion, self.settings.exercise_motion_threshold)
        elif (
            self._history_ready()
            and upright
            and alternations >= 1
            and motion >= self.settings.walking_motion_threshold
        ):
            label = ActivityLabel.WALKING
            margin = self._above_margin(motion, self.settings.walking_motion_threshold)
        elif upright and (
            features.mean_hip_angle <= self.settings.sitting_joint_angle
            or features.mean_knee_angle <= self.settings.sitting_joint_angle
        ):
            label = ActivityLabel.SITTING
            flexion = min(features.mean_hip_angle, features.mean_knee_angle)
            margin = self._below_margin(flexion, self.settings.sitting_joint_angle)
        elif upright and (
            features.mean_hip_angle >= self.settings.standing_joint_angle
            and features.mean_knee_angle >= self.settings.standing_joint_angle
        ):
            label = ActivityLabel.STANDING
            extension = min(features.mean_hip_angle, features.mean_knee_angle)
            margin = self._above_margin(extension, self.settings.standing_joint_angle, 180.0)
        else:
            label = ActivityLabel.UNKNOWN
            margin = 0.0

        temporal = self._temporal_consistency(label)
        self._labels.append(label)
        if label is ActivityLabel.UNKNOWN:
            confidence = min(0.25, features.mean_visibility * 0.25)
        else:
            confidence = 0.5 * features.mean_visibility + 0.3 * margin + 0.2 * temporal
        return ClassificationResult(
            label=label,
            confidence=round(max(0.0, min(1.0, confidence)), 4),
            orientation=orientation,
            features=features,
        )

    def _unknown(self) -> ClassificationResult:
        self._history.clear()
        self._labels.append(ActivityLabel.UNKNOWN)
        return ClassificationResult(ActivityLabel.UNKNOWN, 0.05, Orientation.UNKNOWN)

    def _orientation(self, angle: float) -> Orientation:
        horizontal_start = 90.0 - self.settings.horizontal_angle_threshold
        return Orientation.HORIZONTAL if angle >= horizontal_start else Orientation.VERTICAL

    def _horizontal_margin(self, angle: float) -> float:
        boundary = 90.0 - self.settings.horizontal_angle_threshold
        return self._above_margin(angle, boundary, 90.0)

    @staticmethod
    def _above_margin(value: float, threshold: float, maximum: float | None = None) -> float:
        ceiling = maximum if maximum is not None else max(threshold * 2.0, threshold + 1e-9)
        return max(0.0, min(1.0, (value - threshold) / (ceiling - threshold)))

    @staticmethod
    def _below_margin(value: float, threshold: float) -> float:
        return max(0.0, min(1.0, (threshold - value) / max(threshold, 1e-9)))

    def _history_ready(self) -> bool:
        return len(self._history) >= max(3, self.settings.motion_history_length // 2)

    def _temporal_metrics(self) -> tuple[float, int, bool]:
        if len(self._history) < 2:
            return 0.0, 0, False
        motions: list[float] = []
        history = tuple(self._history)
        for previous, current in zip(history, history[1:], strict=False):
            previous_points = {name: (x, y) for name, x, y in previous.coordinates}
            current_points = {name: (x, y) for name, x, y in current.coordinates}
            common = previous_points.keys() & current_points.keys()
            if common:
                motions.append(
                    sum(
                        math.hypot(
                            current_points[name][0] - previous_points[name][0],
                            current_points[name][1] - previous_points[name][1],
                        )
                        for name in common
                    )
                    / len(common)
                )
        motion = sum(motions) / len(motions) if motions else 0.0
        signs = [
            1 if item.ankle_offset > 0.005 else -1 if item.ankle_offset < -0.005 else 0
            for item in self._history
        ]
        non_zero = [sign for sign in signs if sign]
        alternations = sum(
            first != second for first, second in zip(non_zero, non_zero[1:], strict=False)
        )

        signals = [item.movement_signal for item in self._history]
        deltas = [second - first for first, second in zip(signals, signals[1:], strict=False)]
        directions = [1 if value > 0.002 else -1 if value < -0.002 else 0 for value in deltas]
        non_zero_directions = [direction for direction in directions if direction]
        repetitions = sum(
            first != second
            for first, second in zip(non_zero_directions, non_zero_directions[1:], strict=False)
        )
        return motion, alternations, repetitions >= 1

    def _temporal_consistency(self, label: ActivityLabel) -> float:
        if not self._labels:
            return 0.5
        counts = Counter(self._labels)
        return counts[label] / len(self._labels)
