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


def standing_pose_at(drop: float = 0.0) -> PoseLandmarks:
    """An upright body whose every joint is shifted ``drop`` down the frame.

    Framed high enough that a full fall keeps the ankles inside the image, so
    the pose stays observed rather than extrapolated.
    """

    return PoseLandmarks(
        {
            "left_shoulder": Landmark(0.4, 0.05 + drop),
            "right_shoulder": Landmark(0.6, 0.05 + drop),
            "left_hip": Landmark(0.4, 0.30 + drop),
            "right_hip": Landmark(0.6, 0.30 + drop),
            "left_knee": Landmark(0.4, 0.48 + drop),
            "right_knee": Landmark(0.6, 0.48 + drop),
            "left_ankle": Landmark(0.4, 0.66 + drop),
            "right_ankle": Landmark(0.6, 0.66 + drop),
            "left_wrist": Landmark(0.3, 0.25 + drop),
            "right_wrist": Landmark(0.7, 0.25 + drop),
        }
    )


def test_standing_still_reports_no_vertical_velocity() -> None:
    classifier = ActivityClassifier(VideoSettings(fps=10.0))

    result = None
    for _ in range(6):
        result = classifier.classify(standing_pose_at(0.0))

    assert result is not None
    assert result.vertical_velocity == pytest.approx(0.0, abs=0.01)


def test_a_body_dropping_down_the_frame_reports_downward_velocity() -> None:
    classifier = ActivityClassifier(VideoSettings(fps=10.0))
    for _ in range(4):
        classifier.classify(standing_pose_at(0.0))

    # 0.06 of frame height per frame at 10 FPS is 0.6 frame-heights per second.
    result = None
    for step in range(1, 5):
        result = classifier.classify(standing_pose_at(0.06 * step))

    assert result is not None
    assert result.vertical_velocity == pytest.approx(0.6, abs=0.05)


def test_a_body_rising_reports_negative_vertical_velocity() -> None:
    classifier = ActivityClassifier(VideoSettings(fps=10.0))
    for step in range(4, 0, -1):
        classifier.classify(standing_pose_at(0.06 * step))

    result = classifier.classify(standing_pose_at(0.0))

    assert result.vertical_velocity < 0.0


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


def extrapolated_offscreen_pose() -> PoseLandmarks:
    """A pose MediaPipe invents when most of the body is outside the frame.

    These coordinates are recorded from a real DroidCam session in which the
    person was standing but only their upper body was framed.  MediaPipe does
    not report the unseen joints as missing; it extrapolates them far past the
    left edge and still labels them 99% visible.  The invented skeleton is a
    horizontal line, which reads as a torso angle of ~87 degrees.
    """

    return PoseLandmarks(
        {
            "left_shoulder": Landmark(0.12, 0.50, visibility=0.99),
            "right_shoulder": Landmark(0.12, 0.64, visibility=0.99),
            "left_hip": Landmark(-0.56, 0.50, visibility=0.99),
            "right_hip": Landmark(-0.56, 0.64, visibility=0.99),
            "left_knee": Landmark(-1.04, 0.51, visibility=0.99),
            "right_knee": Landmark(-1.04, 0.65, visibility=0.99),
            "left_ankle": Landmark(-1.53, 0.58, visibility=0.99),
            "right_ankle": Landmark(-1.53, 0.72, visibility=0.99),
            "left_wrist": Landmark(-0.30, 0.40, visibility=0.99),
            "right_wrist": Landmark(-0.30, 0.70, visibility=0.99),
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


def test_landmarks_extrapolated_outside_the_frame_are_not_trusted() -> None:
    """High visibility is not evidence that a joint was actually seen.

    Reporting a confident LYING for a standing person is worse than admitting
    the pose is unusable: it is the false fall alarm this system exists to
    avoid.
    """

    result = ActivityClassifier(VideoSettings()).classify(extrapolated_offscreen_pose())
    assert result.label is ActivityLabel.UNKNOWN
    assert result.confidence <= 0.1


def test_a_joint_exactly_on_the_frame_edge_is_still_usable() -> None:
    """Someone filling the frame is framed correctly, not unusable.

    The edge itself is inside the image, so it must not be rejected: that is
    the difference between a strict bound and a useless one.
    """

    pose = PoseLandmarks(
        {
            "left_shoulder": Landmark(0.4, 0.0),
            "right_shoulder": Landmark(0.6, 0.0),
            "left_hip": Landmark(0.4, 0.4),
            "right_hip": Landmark(0.6, 0.4),
            "left_knee": Landmark(0.4, 0.7),
            "right_knee": Landmark(0.6, 0.7),
            "left_ankle": Landmark(0.0, 1.0),
            "right_ankle": Landmark(1.0, 1.0),
            "left_wrist": Landmark(0.3, 0.3),
            "right_wrist": Landmark(0.7, 0.3),
        }
    )
    assert ActivityClassifier(VideoSettings()).classify(pose).label is not ActivityLabel.UNKNOWN


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
    # Rotate the complete skeleton 65 degrees about the middle of the frame, so
    # the person stays inside the image the way a real one would. The torso then
    # sits exactly at the configured horizontal boundary (90 - 25 degrees).
    radians = math.radians(65)
    pivot = 0.5
    rotated = PoseLandmarks(
        {
            name: Landmark(
                pivot
                + (point.x - pivot) * math.cos(radians)
                - (point.y - pivot) * math.sin(radians),
                pivot
                + (point.x - pivot) * math.sin(radians)
                + (point.y - pivot) * math.cos(radians),
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
