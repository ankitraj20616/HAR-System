import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from services.fusion_service.config import FusionSettings
from services.fusion_service.fusion import (
    FusionEngine,
    PredictionBuffer,
    TemporalSmoother,
    confidence_weighted_vote,
)
from shared.labels import ActivityLabel
from shared.schemas import SensorPrediction, VideoPrediction

BASE = datetime(2026, 6, 20, 10, tzinfo=UTC)


def sensor(
    offset: float,
    label: str = "WALKING",
    confidence: float = 0.8,
    motion: float = 0.2,
) -> SensorPrediction:
    return SensorPrediction(
        ts=BASE + timedelta(seconds=offset),
        modality="sensor",
        label=label,
        confidence=confidence,
        motion_intensity=motion,
    )


def video(
    offset: float,
    label: str = "WALKING",
    confidence: float = 0.8,
    orientation: str = "vertical",
) -> VideoPrediction:
    return VideoPrediction(
        ts=BASE + timedelta(seconds=offset),
        modality="video",
        label=label,
        confidence=confidence,
        orientation=orientation,
    )


def settings(**changes: object) -> FusionSettings:
    values: dict[str, object] = {
        "alignment_tolerance_ms": 500,
        "buffer_retention_ms": 5000,
        "stale_timeout_seconds": 2.0,
        "smoothing_window": 5,
    }
    values.update(changes)
    return FusionSettings(**values)


class TestFusionSettings:
    def test_documented_environment_weight_syntax_and_duration_properties(self) -> None:
        environment = {
            "MODALITY_WEIGHTS": " sensor=0.75, video=0.25 ",
            "ALIGNMENT_TOLERANCE_MS": "1300",
            "BUFFER_RETENTION_MS": "8000",
            "STALE_TIMEOUT_SECONDS": "2.5",
            "FUSION_INTERVAL": "0.5",
        }
        with patch.dict(os.environ, environment, clear=True):
            configured = FusionSettings()

        assert configured.modality_weights == {"sensor": 0.75, "video": 0.25}
        assert configured.normalized_modality_weights == {"sensor": 0.75, "video": 0.25}
        assert configured.alignment_tolerance == timedelta(seconds=1.3)
        assert configured.buffer_retention == timedelta(seconds=8)
        assert configured.stale_timeout == timedelta(seconds=2.5)
        assert configured.fusion_interval == 0.5

    def test_json_and_mapping_weights_are_normalized(self) -> None:
        from_json = FusionSettings(modality_weights='{"sensor": 2, "video": 1}')
        from_mapping = FusionSettings(modality_weights={" SENSOR ": "3", "Video": 1})

        assert from_json.modality_weights == {"sensor": 2.0, "video": 1.0}
        assert from_json.normalized_modality_weights == pytest.approx(
            {"sensor": 2 / 3, "video": 1 / 3}
        )
        assert from_mapping.modality_weights == {"sensor": 3.0, "video": 1.0}

    @pytest.mark.parametrize(
        "weights",
        [
            "",
            "sensor=0.5",
            "sensor=0.5,video=0.5,sensor=1",
            "sensor=0.5,video=nope",
            "sensor=0.5,other=0.5",
            "sensor=0,video=1",
            "sensor=nan,video=1",
            {"sensor": True, "video": 1},
        ],
    )
    def test_invalid_modality_weights_are_rejected(self, weights: object) -> None:
        with pytest.raises(ValidationError):
            FusionSettings(modality_weights=weights)

    @pytest.mark.parametrize(
        "changes",
        [
            {"smoothing_window": 0},
            {"fusion_interval": 0},
            {"buffer_max_size": 0},
            {"api_max_limit": 0},
            {"abnormal_baseline_samples": 1},
            {"abnormal_baseline_multiplier": 1.0},
            {"alignment_tolerance_ms": 1501, "buffer_retention_ms": 1500},
            {"alignment_tolerance_ms": 1501, "stale_timeout_seconds": 1.5},
        ],
    )
    def test_invalid_or_incoherent_settings_are_rejected(self, changes: dict[str, object]) -> None:
        with pytest.raises(ValidationError):
            FusionSettings(**changes)


class TestPredictionBuffer:
    def test_orders_out_of_order_inputs_and_deduplicates_by_timestamp(self) -> None:
        buffer = PredictionBuffer("sensor", retention=timedelta(seconds=10), max_size=10)

        assert buffer.add(sensor(2)).accepted
        assert buffer.add(sensor(1)).accepted
        duplicate = buffer.add(sensor(1, label="SITTING"))

        assert duplicate.status == "duplicate"
        assert buffer.timestamps == (BASE + timedelta(seconds=1), BASE + timedelta(seconds=2))

    def test_retention_and_max_size_are_bounded_and_old_input_is_late(self) -> None:
        buffer = PredictionBuffer("sensor", retention=timedelta(seconds=2), max_size=2)
        assert buffer.add(sensor(0)).accepted
        assert buffer.add(sensor(1)).accepted
        capped = buffer.add(sensor(2))
        retained = buffer.add(sensor(4))
        late = buffer.add(sensor(0))

        assert capped.evicted == 1
        assert retained.evicted == 1
        assert buffer.timestamps == (BASE + timedelta(seconds=2), BASE + timedelta(seconds=4))
        assert late.status == "late"

    def test_selects_nearest_consumes_it_and_prefers_earlier_exact_tie(self) -> None:
        buffer = PredictionBuffer("video", retention=timedelta(seconds=10), max_size=10)
        before = video(0.9, label="SITTING")
        after = video(1.1, label="STANDING")
        buffer.add(after)
        buffer.add(before)

        selected = buffer.select_nearest(
            BASE + timedelta(seconds=1),
            tolerance=timedelta(milliseconds=200),
            stale_timeout=timedelta(seconds=2),
        )

        assert selected.prediction is before
        assert buffer.timestamps == (after.ts,)
        # Consumed identities remain deduplicated while the buffer horizon is active.
        assert buffer.add(before).status == "duplicate"

    def test_discards_stale_alignment_expired_and_superseded_predictions(self) -> None:
        buffer = PredictionBuffer("sensor", retention=timedelta(seconds=20), max_size=20)
        for offset in (0, 2.5, 3.7, 3.9):
            buffer.add(sensor(offset))

        selected = buffer.select_nearest(
            BASE + timedelta(seconds=4),
            tolerance=timedelta(seconds=0.5),
            stale_timeout=timedelta(seconds=2),
        )

        assert selected.prediction is not None
        assert selected.prediction.ts == BASE + timedelta(seconds=3.9)
        assert selected.stale_discarded == 1
        assert selected.alignment_expired == 1
        assert selected.superseded == 1
        assert len(buffer) == 0

    def test_rejects_wrong_modality_and_non_utc_target(self) -> None:
        buffer = PredictionBuffer("sensor", retention=timedelta(seconds=5), max_size=5)
        with pytest.raises(ValueError, match="cannot accept"):
            buffer.add(video(0))
        with pytest.raises(ValueError, match="timezone-aware UTC"):
            buffer.select_nearest(
                datetime(2026, 1, 1),
                tolerance=timedelta(seconds=1),
                stale_timeout=timedelta(seconds=2),
            )


class TestVotingAndSmoothing:
    def test_agreement_accumulates_weighted_confidence(self) -> None:
        result = confidence_weighted_vote(
            sensor(0, confidence=0.9),
            video(0, confidence=0.7),
            modality_weights={"sensor": 0.5, "video": 0.5},
        )

        assert result.label == ActivityLabel.WALKING
        assert result.confidence == pytest.approx(0.8)
        assert result.scores == {ActivityLabel.WALKING: pytest.approx(0.8)}

    def test_disagreement_uses_weight_times_confidence_not_confidence_alone(self) -> None:
        result = confidence_weighted_vote(
            sensor(0, label="WALKING", confidence=0.6),
            video(0, label="STANDING", confidence=0.9),
            modality_weights={"sensor": 0.8, "video": 0.2},
        )

        assert result.label == ActivityLabel.WALKING
        assert result.scores[ActivityLabel.WALKING] == pytest.approx(0.48)
        assert result.scores[ActivityLabel.STANDING] == pytest.approx(0.18)

    def test_single_source_normalizes_active_weight(self) -> None:
        result = confidence_weighted_vote(
            sensor(0, label="SITTING", confidence=0.73),
            None,
            modality_weights={"sensor": 0.1, "video": 0.9},
        )

        assert result.label == ActivityLabel.SITTING
        assert result.confidence == pytest.approx(0.73)
        assert result.active_weights == {"sensor": 1.0}

    def test_tie_prefers_previous_stable_then_unknown(self) -> None:
        args = (
            sensor(0, label="WALKING", confidence=0.8),
            video(0, label="STANDING", confidence=0.8),
        )
        no_previous = confidence_weighted_vote(
            *args, modality_weights={"sensor": 0.5, "video": 0.5}
        )
        previous = confidence_weighted_vote(
            *args,
            modality_weights={"sensor": 0.5, "video": 0.5},
            previous_stable=ActivityLabel.STANDING,
        )

        assert no_previous.label == ActivityLabel.UNKNOWN
        assert previous.label == ActivityLabel.STANDING

    def test_no_predictions_or_missing_weight_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            confidence_weighted_vote(None, None, modality_weights={"sensor": 0.5, "video": 0.5})
        with pytest.raises(ValueError, match="missing weight"):
            confidence_weighted_vote(sensor(0), None, modality_weights={"video": 1.0})

    def test_smoothing_rejects_isolated_flicker_then_changes_on_majority(self) -> None:
        smoother = TemporalSmoother(window_size=5)
        first = smoother.update("WALKING", 0.9)
        noisy = smoother.update("SITTING", 0.8)
        smoother.update("SITTING", 0.7)
        changed = smoother.update("SITTING", 0.6)

        assert first.stable_label == ActivityLabel.WALKING
        assert noisy.raw_label == ActivityLabel.SITTING
        assert noisy.stable_label == ActivityLabel.WALKING
        assert noisy.stable_confidence == pytest.approx(0.9)
        assert changed.stable_label == ActivityLabel.SITTING
        assert changed.stable_confidence == pytest.approx(0.7)


class TestFusionEngine:
    def test_fuses_aligned_sources_and_exposes_raw_stable_and_diagnostics(self) -> None:
        engine = FusionEngine(settings())
        sensor_prediction = sensor(1, confidence=0.88)
        video_prediction = video(1.05, confidence=0.82)
        assert engine.add(sensor_prediction)
        assert engine.add(video_prediction)

        decision = engine.fuse(BASE + timedelta(seconds=1))

        assert decision is not None
        assert decision.sensor is sensor_prediction
        assert decision.video is video_prediction
        assert decision.raw_label == ActivityLabel.WALKING
        assert decision.stable_label == ActivityLabel.WALKING
        assert decision.activity.activity == "WALKING"
        assert decision.activity.confidence == pytest.approx(0.85)
        assert decision.activity.contributors.sensor == "WALKING"
        assert decision.source_latency_seconds == 0.0
        diagnostics = engine.diagnostics
        assert diagnostics["counters"]["decisions"] == 1
        assert diagnostics["last_received"] == {
            "sensor": sensor_prediction.ts,
            "video": video_prediction.ts,
        }
        assert diagnostics["raw_label"] == "WALKING"
        assert diagnostics["stable_label"] == "WALKING"
        assert diagnostics["buffer_sizes"] == {"sensor": 0, "video": 0}

    def test_consumes_inputs_and_returns_none_when_no_fresh_source_exists(self) -> None:
        engine = FusionEngine(settings())
        engine.add(sensor(1))
        assert engine.fuse(BASE + timedelta(seconds=1)) is not None

        assert engine.fuse(BASE + timedelta(seconds=2)) is None
        assert engine.diagnostics["counters"]["empty_intervals"] == 1

    def test_single_modality_degraded_fusion_and_duplicate_counters(self) -> None:
        engine = FusionEngine(settings(modality_weights={"sensor": 0.2, "video": 0.8}))
        prediction = sensor(1, label="SITTING", confidence=0.72)
        accepted = engine.add(prediction)
        duplicate = engine.add(prediction)
        decision = engine.fuse(BASE + timedelta(seconds=1))

        assert accepted.status == "accepted"
        assert duplicate.status == "duplicate"
        assert decision is not None
        assert decision.video is None
        assert decision.raw_label == ActivityLabel.SITTING
        assert decision.raw_confidence == pytest.approx(0.72)
        assert decision.active_weights == {"sensor": 1.0}
        assert engine.diagnostics["counters"]["duplicates"]["sensor"] == 1

    def test_stale_and_alignment_expired_messages_do_not_create_activity(self) -> None:
        engine = FusionEngine(settings())
        engine.add(sensor(0))
        result = engine.fuse(BASE + timedelta(seconds=3))

        assert result is None
        counters = engine.diagnostics["counters"]
        assert counters["stale"]["sensor"] == 1
        assert counters["empty_intervals"] == 1

    def test_engine_smoothing_keeps_stable_label_during_one_noisy_interval(self) -> None:
        engine = FusionEngine(settings(alignment_tolerance_ms=100))
        for offset, label in ((0, "WALKING"), (1, "WALKING"), (2, "SITTING")):
            engine.add(sensor(offset, label=label, confidence=0.9))
            decision = engine.fuse(BASE + timedelta(seconds=offset))
            assert decision is not None

        assert decision.raw_label == ActivityLabel.SITTING
        assert decision.stable_label == ActivityLabel.WALKING
        assert decision.activity.activity == "WALKING"

    def test_rejects_invalid_input_type_and_non_utc_tick(self) -> None:
        engine = FusionEngine(settings())
        with pytest.raises(TypeError, match="SensorPrediction"):
            engine.add(object())  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="timezone-aware UTC"):
            engine.fuse(datetime(2026, 1, 1))
