"""Unit tests for deterministic Milestone 3 safety state machines."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from services.fusion_service.safety import (
    AbnormalPatternDetector,
    FallDetector,
    InactivityDetector,
    SafetyEngine,
)
from shared.schemas import FusedActivity, SensorPrediction, VideoPrediction

START = datetime(2026, 7, 10, 10, tzinfo=UTC)


def sensor(
    seconds: float,
    *,
    motion: float = 3.0,
    label: str = "UNKNOWN",
    confidence: float = 0.9,
) -> SensorPrediction:
    return SensorPrediction(
        ts=START + timedelta(seconds=seconds),
        modality="sensor",
        label=label,
        confidence=confidence,
        motion_intensity=motion,
    )


def video(
    seconds: float,
    *,
    orientation: str = "horizontal",
    label: str = "LYING",
    confidence: float = 0.8,
    velocity: float = 0.0,
) -> VideoPrediction:
    return VideoPrediction(
        ts=START + timedelta(seconds=seconds),
        modality="video",
        label=label,
        confidence=confidence,
        orientation=orientation,
        vertical_velocity=velocity,
    )


def activity(seconds: float, label: str = "LYING", confidence: float = 0.85) -> FusedActivity:
    return FusedActivity(
        ts=START + timedelta(seconds=seconds),
        activity=label,
        confidence=confidence,
        contributors={"sensor": label},
    )


def fall_detector(**changes: float) -> FallDetector:
    values = {
        "fall_accel_threshold": 2.5,
        "fall_correlation_ms": 500,
        "fall_cooldown_seconds": 5,
        "fall_recovery_timeout_seconds": 10,
        "inactivity_motion_threshold": 0.1,
        "fall_velocity_threshold": 0.6,
    }
    values.update(changes)
    return FallDetector(**values)


def test_a_fast_drop_into_horizontal_raises_a_fall_without_any_sensor() -> None:
    detector = fall_detector()

    event = detector.process(video(0.0, velocity=1.2))

    assert event is not None
    assert event.type == "FALL"
    assert event.evidence["two_modality_confirmed"] is False
    assert event.evidence["rule"] == "video_drop_and_horizontal"


def test_settling_slowly_into_horizontal_raises_no_fall_without_a_sensor() -> None:
    detector = fall_detector()

    assert detector.process(video(0.0, velocity=0.1)) is None


def test_a_fast_drop_while_still_upright_raises_no_fall() -> None:
    detector = fall_detector()

    assert detector.process(video(0.0, orientation="vertical", velocity=1.2)) is None


def test_a_sensor_spike_still_upgrades_a_video_fall_to_two_modality() -> None:
    detector = fall_detector()

    detector.process(sensor(0.0, motion=3.0))
    event = detector.process(video(0.2, velocity=1.2))

    assert event is not None
    assert event.evidence["two_modality_confirmed"] is True
    assert event.evidence["rule"] == "motion_spike_and_horizontal"


@pytest.mark.parametrize("video_first", [False, True])
def test_fall_correlates_on_event_time_in_either_arrival_order(video_first: bool) -> None:
    detector = fall_detector()
    pair = [sensor(0.0, motion=2.5), video(0.4)]
    if video_first:
        pair.reverse()

    assert detector.process(pair[0]) is None
    event = detector.process(pair[1])

    assert event is not None
    assert event.type == "FALL"
    assert event.severity == "critical"
    assert event.confidence == 0.8
    assert event.ts == START + timedelta(seconds=0.4)
    assert event.evidence["two_modality_confirmed"] is True
    assert event.evidence["sensor"]["motion_intensity"] == 2.5
    assert event.evidence["video"]["orientation"] == "horizontal"
    assert event.evidence["thresholds"]["fall_accel_threshold"] == 2.5
    assert event.evidence["correlation_ms"] == pytest.approx(400)
    json.dumps(event.evidence, allow_nan=False)


def test_fall_requires_both_modalities_within_inclusive_correlation_window() -> None:
    spike_only = fall_detector()
    horizontal_only = fall_detector()
    ordinary_lying = fall_detector()
    too_late = fall_detector()
    boundary = fall_detector()

    assert spike_only.process(sensor(0)) is None
    assert horizontal_only.process(video(0)) is None
    assert ordinary_lying.process(sensor(0, motion=0.01, label="LYING")) is None
    assert ordinary_lying.process(video(0.1)) is None
    assert too_late.process(sensor(0)) is None
    assert too_late.process(video(0.501)) is None
    assert boundary.process(sensor(0)) is None
    assert boundary.process(video(0.5)) is not None


def test_duplicate_evidence_and_cooldown_produce_exactly_one_fall() -> None:
    detector = fall_detector()
    spike = sensor(0)
    horizontal = video(0.1)

    assert detector.process(spike) is None
    assert detector.process(horizontal) is not None
    assert detector.process(spike) is None
    assert detector.process(horizontal) is None
    assert detector.process(sensor(1)) is None
    assert detector.process(video(1.1)) is None
    assert detector.armed is False


def test_fall_rearms_after_cooldown_and_complete_recovery() -> None:
    detector = fall_detector()
    detector.process(sensor(0))
    assert detector.process(video(0.1)) is not None

    assert detector.process(sensor(1, motion=0.05, label="STANDING")) is None
    assert detector.process(video(1.1, orientation="vertical", label="STANDING")) is None
    assert detector.process(sensor(5.1)) is None
    second = detector.process(video(5.2))

    assert second is not None
    assert second.type == "FALL"


def test_partial_recovery_does_not_rearm_before_timeout() -> None:
    detector = fall_detector()
    detector.process(sensor(0))
    assert detector.process(video(0.1)) is not None
    detector.process(sensor(1, motion=0.01))

    assert detector.process(sensor(6)) is None
    assert detector.process(video(6.1)) is None
    assert detector.armed is False

    # Timeout is measured in event time and can re-arm without recovery.
    assert detector.process(sensor(10.2)) is None
    assert detector.process(video(10.3)) is not None


def test_fall_rejects_wrong_types_and_invalid_configuration() -> None:
    detector = fall_detector()
    with pytest.raises(TypeError, match="SensorPrediction or VideoPrediction"):
        detector.process(activity(0))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fall_accel_threshold"):
        fall_detector(fall_accel_threshold=0)


def test_inactivity_is_one_shot_until_meaningful_motion_resets_it() -> None:
    detector = InactivityDetector(inactivity_seconds=10, inactivity_motion_threshold=0.1)

    assert detector.process(activity(0, "LYING"), sensor(0, motion=0.01, label="LYING")) is None
    event = detector.process(activity(10, "SITTING"), sensor(10, motion=0.02, label="SITTING"))
    assert event is not None
    assert event.type == "INACTIVITY"
    assert event.severity == "warning"
    assert event.evidence["duration_seconds"] == 10
    assert (
        detector.process(activity(20, "STANDING"), sensor(20, motion=0.01, label="STANDING"))
        is None
    )

    assert (
        detector.process(activity(21, "WALKING"), sensor(21, motion=0.5, label="WALKING")) is None
    )
    assert detector.process(activity(22, "LYING"), sensor(22, motion=0.01, label="LYING")) is None
    assert (
        detector.process(activity(32, "LYING"), sensor(32, motion=0.01, label="LYING")) is not None
    )


def test_inactivity_requires_fresh_sensor_evidence_and_ignores_unknown() -> None:
    detector = InactivityDetector(inactivity_seconds=5, inactivity_motion_threshold=0.1)

    assert detector.process(activity(0), sensor(0, motion=0.01)) is None
    assert detector.process(activity(5), None) is None
    assert detector.process(activity(10), sensor(10, motion=0.01)) is None
    assert (
        detector.process(activity(20, "UNKNOWN"), sensor(20, motion=0.01, label="UNKNOWN")) is None
    )
    assert detector.process(activity(25), sensor(25, motion=0.01)) is None


def test_inactivity_ignores_late_observation_without_corrupting_state() -> None:
    detector = InactivityDetector(inactivity_seconds=10, inactivity_motion_threshold=0.1)
    detector.process(activity(10), sensor(10, motion=0.01))

    assert detector.process(activity(5), sensor(5, motion=0.01)) is None
    event = detector.process(activity(20), sensor(20, motion=0.01))
    assert event is not None
    assert event.evidence["start_ts"] == "2026-07-10T10:00:10Z"


def abnormal_detector() -> AbnormalPatternDetector:
    return AbnormalPatternDetector(
        abnormal_min_seconds=15,
        abnormal_baseline_samples=3,
        abnormal_baseline_multiplier=2,
    )


def seed_three_ten_second_lying_runs(detector: AbnormalPatternDetector) -> None:
    for timestamp, label in (
        (0, "LYING"),
        (10, "WALKING"),
        (11, "LYING"),
        (21, "WALKING"),
        (22, "LYING"),
        (32, "WALKING"),
        (33, "LYING"),
    ):
        assert detector.process(activity(timestamp, label)) is None


def test_abnormal_pattern_uses_completed_run_median_and_emits_once() -> None:
    detector = abnormal_detector()
    seed_three_ten_second_lying_runs(detector)

    assert detector.process(activity(53, "LYING")) is not None
    event = detector.process(activity(54, "LYING"))
    assert event is None

    # Inspect a fresh detector's first event for the explainable baseline.
    detector = abnormal_detector()
    seed_three_ten_second_lying_runs(detector)
    event = detector.process(activity(53, "LYING"))
    assert event is not None
    assert event.type == "ABNORMAL_PATTERN"
    assert event.evidence["completed_run_durations_seconds"] == [10.0, 10.0, 10.0]
    assert event.evidence["baseline_median_seconds"] == 10
    assert event.evidence["threshold_seconds"] == 20
    assert event.evidence["duration_seconds"] == 20
    json.dumps(event.evidence, allow_nan=False)


def test_abnormal_pattern_needs_full_baseline_and_excludes_unknown_runs() -> None:
    detector = abnormal_detector()
    detector.process(activity(0, "LYING"))
    detector.process(activity(10, "UNKNOWN"))
    detector.process(activity(100, "LYING"))

    assert detector.process(activity(200, "LYING")) is None


def test_abnormal_pattern_absolute_minimum_can_dominate_median_rule() -> None:
    detector = AbnormalPatternDetector(
        abnormal_min_seconds=30,
        abnormal_baseline_samples=1,
        abnormal_baseline_multiplier=2,
    )
    detector.process(activity(0, "SITTING"))
    detector.process(activity(10, "WALKING"))
    detector.process(activity(11, "SITTING"))

    assert detector.process(activity(40, "SITTING")) is None
    assert detector.process(activity(41, "SITTING")) is not None


def test_safety_engine_returns_zero_or_more_events_with_predictable_api() -> None:
    engine = SafetyEngine(
        fall_accel_threshold=2.5,
        fall_correlation_ms=500,
        fall_cooldown_seconds=5,
        fall_recovery_timeout_seconds=10,
        inactivity_seconds=10,
        inactivity_motion_threshold=0.1,
        abnormal_min_seconds=30,
        abnormal_baseline_samples=3,
        abnormal_baseline_multiplier=2,
    )

    assert engine.process_prediction(sensor(0)) == ()
    falls = engine.process_prediction(video(0.1))
    assert len(falls) == 1
    assert falls[0].type == "FALL"
    assert engine.process_activity(activity(0), sensor(0, motion=0.01)) == ()
