"""Synthetic geometry tests for deterministic video activity rules."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from services.video_service.classifier import ActivityClassifier
from services.video_service.config import VideoSettings
from services.video_service.landmarks import Landmark, PoseLandmarks, three_point_angle
from shared.labels import ActivityLabel, Orientation


def standing_pose(
    *, visibility: float = 1.0, ankle_offset: float = 0.0, wrist_y: float = 0.45
) -> PoseLandmarks:
    return PoseLandmarks(
        {
            "left_shoulder": Landmark(0.4, 0.2, visibility=visibility),
            "right_shoulder": Landmark(0.6, 0.2, visibility=visibility),
            "left_hip": Landmark(0.4, 0.5, visibility=visibility),
            "right_hip": Landmark(0.6, 0.5, visibility=visibility),
            "left_knee": Landmark(0.4, 0.7, visibility=visibility),
            "right_knee": Landmark(0.6, 0.7, visibility=visibility),
            "left_ankle": Landmark(0.4, 0.9 + ankle_offset, visibility=visibility),
            "right_ankle": Landmark(0.6, 0.9 - ankle_offset, visibility=visibility),
            "left_wrist": Landmark(0.3, wrist_y, visibility=visibility),
            "right_wrist": Landmark(0.7, wrist_y, visibility=visibility),
        }
    )


def sitting_pose() -> PoseLandmarks:
    return PoseLandmarks(
        {
            "left_shoulder": Landmark(0.3, 0.2),
            "right_shoulder": Landmark(0.5, 0.2),
            "left_hip": Landmark(0.3, 0.5),
            "right_hip": Landmark(0.5, 0.5),
            "left_knee": Landmark(0.55, 0.5),
            "right_knee": Landmark(0.75, 0.5),
            "left_ankle": Landmark(0.55, 0.8),
            "right_ankle": Landmark(0.75, 0.8),
            "left_wrist": Landmark(0.25, 0.45),
            "right_wrist": Landmark(0.55, 0.45),
        }
    )


def lying_pose() -> PoseLandmarks:
    return PoseLandmarks(
        {
            "left_shoulder": Landmark(0.2, 0.4),
            "right_shoulder": Landmark(0.2, 0.5),
            "left_hip": Landmark(0.5, 0.4),
            "right_hip": Landmark(0.5, 0.5),
            "left_knee": Landmark(0.7, 0.4),
            "right_knee": Landmark(0.7, 0.5),
            "left_ankle": Landmark(0.9, 0.4),
            "right_ankle": Landmark(0.9, 0.5),
            "left_wrist": Landmark(0.3, 0.3),
            "right_wrist": Landmark(0.3, 0.6),
        }
    )


def translate(pose: PoseLandmarks, dx: float = 0.0, dy: float = 0.0) -> PoseLandmarks:
    points = {}
    for name, point in pose.visible().items():
        points[name] = Landmark(point.x + dx, point.y + dy, point.z, point.visibility)
    return PoseLandmarks(points)


def test_three_point_angle_is_reusable_and_rejects_degenerate_geometry() -> None:
    assert three_point_angle(Landmark(0, 1), Landmark(0, 0), Landmark(1, 0)) == 90.0
    assert three_point_angle(Landmark(0, -1), Landmark(0, 0), Landmark(0, 1)) == 180.0
    with pytest.raises(ValueError, match="coincident"):
        three_point_angle(Landmark(0, 0), Landmark(0, 0), Landmark(1, 0))


@pytest.mark.parametrize(
    ("pose", "expected_label", "expected_orientation"),
    [
        (standing_pose(), ActivityLabel.STANDING, Orientation.VERTICAL),
        (sitting_pose(), ActivityLabel.SITTING, Orientation.VERTICAL),
        (lying_pose(), ActivityLabel.LYING, Orientation.HORIZONTAL),
    ],
)
def test_static_geometric_rules(pose, expected_label, expected_orientation) -> None:
    result = ActivityClassifier(VideoSettings()).classify(pose)
    assert result.label is expected_label
    assert result.orientation is expected_orientation
    assert 0.0 < result.confidence <= 1.0


def test_missing_or_low_visibility_pose_is_unknown_with_low_confidence() -> None:
    classifier = ActivityClassifier(VideoSettings(min_visibility=0.7))
    for pose in (None, PoseLandmarks({}), standing_pose(visibility=0.69)):
        result = classifier.classify(pose)
        assert result.label is ActivityLabel.UNKNOWN
        assert result.orientation is Orientation.UNKNOWN
        assert result.confidence <= 0.1


def test_dynamic_activity_requires_history_then_detects_leg_alternation() -> None:
    settings = VideoSettings(
        motion_history_length=4,
        walking_motion_threshold=0.01,
        exercise_motion_threshold=0.2,
    )
    classifier = ActivityClassifier(settings)
    labels = []
    for index, offset in enumerate((0.04, -0.04, 0.04, -0.04)):
        pose = translate(standing_pose(ankle_offset=offset), dx=index * 0.015)
        labels.append(classifier.classify(pose).label)
    assert labels[0] is ActivityLabel.STANDING
    assert labels[-1] is ActivityLabel.WALKING


def test_repetitive_high_multi_joint_motion_is_exercise() -> None:
    settings = VideoSettings(
        motion_history_length=4,
        walking_motion_threshold=0.01,
        exercise_motion_threshold=0.04,
    )
    classifier = ActivityClassifier(settings)
    result = None
    for wrist_y in (0.25, 0.65, 0.25, 0.65):
        result = classifier.classify(standing_pose(wrist_y=wrist_y))
    assert result is not None
    assert result.label is ActivityLabel.EXERCISING


def test_orientation_threshold_edge_is_horizontal() -> None:
    settings = VideoSettings(horizontal_angle_threshold=25)
    pose = standing_pose()
    points = pose.visible()
    # Rotate the complete skeleton 65 degrees around the origin. The torso is
    # exactly at the configured horizontal boundary (90 - 25 degrees).
    radians = math.radians(65)
    rotated = PoseLandmarks(
        {
            name: Landmark(
                point.x * math.cos(radians) - point.y * math.sin(radians),
                point.x * math.sin(radians) + point.y * math.cos(radians),
                point.z,
                point.visibility,
            )
            for name, point in points.items()
        }
    )
    assert ActivityClassifier(settings).classify(rotated).orientation is Orientation.HORIZONTAL


@pytest.mark.parametrize(
    "values",
    [
        {"fps": 0},
        {"min_visibility": 1.1},
        {"sitting_joint_angle": 160, "standing_joint_angle": 150},
        {"walking_motion_threshold": 0.1, "exercise_motion_threshold": 0.05},
        {"reconnect_initial_backoff": 10, "reconnect_max_backoff": 5},
    ],
)
def test_video_configuration_rejects_unsafe_ranges(values) -> None:
    with pytest.raises(ValidationError):
        VideoSettings(**values)
