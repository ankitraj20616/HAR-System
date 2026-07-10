"""Deterministic safety-event state machines for the fusion service.

The detectors use message timestamps rather than wall-clock time.  This keeps
replay behaviour deterministic and lets delayed sensor/video messages correlate
as long as their event timestamps are inside the configured window.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from math import isfinite
from statistics import median
from typing import TypeAlias

from shared.labels import ActivityLabel, EventSeverity, EventType, Orientation
from shared.schemas import FusedActivity, HAREvent, SensorPrediction, VideoPrediction

Prediction: TypeAlias = SensorPrediction | VideoPrediction


def _seconds(milliseconds: float) -> float:
    return milliseconds / 1000.0


def _iso(timestamp: datetime) -> str:
    return timestamp.isoformat().replace("+00:00", "Z")


def _positive(name: str, value: float, *, allow_zero: bool = False) -> float:
    value = float(value)
    if not isfinite(value) or value < 0.0 or (not allow_zero and value == 0.0):
        comparison = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {comparison}")
    return value


class FallDetector:
    """Correlate a motion spike and horizontal posture into one critical fall.

    Correlation is symmetric: either modality may arrive first.  After an
    event, the detector stays disarmed through the cooldown and then requires
    both low motion and upright posture, unless the recovery timeout expires.
    """

    _SEEN_LIMIT = 2048

    def __init__(
        self,
        *,
        fall_accel_threshold: float,
        fall_correlation_ms: float,
        fall_cooldown_seconds: float,
        fall_recovery_timeout_seconds: float,
        inactivity_motion_threshold: float = 0.05,
    ) -> None:
        self.fall_accel_threshold = _positive("fall_accel_threshold", fall_accel_threshold)
        self.fall_correlation_ms = _positive(
            "fall_correlation_ms", fall_correlation_ms, allow_zero=True
        )
        self.fall_cooldown_seconds = _positive(
            "fall_cooldown_seconds", fall_cooldown_seconds, allow_zero=True
        )
        self.fall_recovery_timeout_seconds = _positive(
            "fall_recovery_timeout_seconds", fall_recovery_timeout_seconds
        )
        self.recovery_motion_threshold = _positive(
            "inactivity_motion_threshold", inactivity_motion_threshold, allow_zero=True
        )

        self._spikes: deque[SensorPrediction] = deque()
        self._horizontal: deque[VideoPrediction] = deque()
        self._seen: set[tuple[object, ...]] = set()
        self._seen_order: deque[tuple[object, ...]] = deque()
        self._watermark: datetime | None = None
        self._last_event_ts: datetime | None = None
        self._armed = True
        self._low_motion_recovered = False
        self._upright_recovered = False

    @property
    def armed(self) -> bool:
        return self._armed

    def process(self, prediction: Prediction) -> HAREvent | None:
        """Consume one strict prediction and return a newly confirmed fall."""

        if not isinstance(prediction, SensorPrediction | VideoPrediction):
            raise TypeError("prediction must be SensorPrediction or VideoPrediction")
        if not self._remember(prediction):
            return None

        self._advance_watermark(prediction.ts)
        self._record_recovery(prediction)
        self._maybe_rearm()
        if not self._armed:
            return None

        if isinstance(prediction, SensorPrediction):
            if prediction.motion_intensity < self.fall_accel_threshold:
                return None
            self._spikes.append(prediction)
            opposite: list[VideoPrediction] = list(self._horizontal)
        else:
            if prediction.orientation != Orientation.HORIZONTAL:
                return None
            self._horizontal.append(prediction)
            opposite = []

        self._prune_candidates()
        if isinstance(prediction, SensorPrediction):
            match = self._nearest(prediction, opposite)
            if match is None:
                return None
            sensor, video = prediction, match
        else:
            match = self._nearest(prediction, list(self._spikes))
            if match is None:
                return None
            sensor, video = match, prediction
        return self._confirm(sensor, video)

    def process_sensor(self, prediction: SensorPrediction) -> HAREvent | None:
        return self.process(prediction)

    def process_video(self, prediction: VideoPrediction) -> HAREvent | None:
        return self.process(prediction)

    def _remember(self, prediction: Prediction) -> bool:
        if isinstance(prediction, SensorPrediction):
            key: tuple[object, ...] = (
                "sensor",
                prediction.ts,
                prediction.label,
                prediction.confidence,
                prediction.motion_intensity,
            )
        else:
            key = (
                "video",
                prediction.ts,
                prediction.label,
                prediction.confidence,
                prediction.orientation,
            )
        if key in self._seen:
            return False
        if len(self._seen_order) >= self._SEEN_LIMIT:
            self._seen.discard(self._seen_order.popleft())
        self._seen.add(key)
        self._seen_order.append(key)
        return True

    def _advance_watermark(self, timestamp: datetime) -> None:
        if self._watermark is None or timestamp > self._watermark:
            self._watermark = timestamp

    def _record_recovery(self, prediction: Prediction) -> None:
        if self._armed or self._last_event_ts is None or prediction.ts < self._last_event_ts:
            return
        if isinstance(prediction, SensorPrediction):
            if prediction.motion_intensity <= self.recovery_motion_threshold:
                self._low_motion_recovered = True
        elif prediction.orientation == Orientation.VERTICAL:
            self._upright_recovered = True

    def _maybe_rearm(self) -> None:
        if self._armed or self._last_event_ts is None or self._watermark is None:
            return
        age = (self._watermark - self._last_event_ts).total_seconds()
        cooldown_elapsed = age >= self.fall_cooldown_seconds
        recovered = self._low_motion_recovered and self._upright_recovered
        timed_out = age >= self.fall_recovery_timeout_seconds
        if cooldown_elapsed and (recovered or timed_out):
            self._armed = True
            self._low_motion_recovered = False
            self._upright_recovered = False
            self._spikes.clear()
            self._horizontal.clear()

    def _prune_candidates(self) -> None:
        if self._watermark is None:
            return
        tolerance = _seconds(self.fall_correlation_ms)
        while self._spikes and (self._watermark - self._spikes[0].ts).total_seconds() > tolerance:
            self._spikes.popleft()
        while (
            self._horizontal
            and (self._watermark - self._horizontal[0].ts).total_seconds() > tolerance
        ):
            self._horizontal.popleft()

    def _nearest(self, prediction: Prediction, candidates: list[Prediction]) -> Prediction | None:
        tolerance = _seconds(self.fall_correlation_ms)
        eligible = [
            candidate
            for candidate in candidates
            if abs((prediction.ts - candidate.ts).total_seconds()) <= tolerance
        ]
        if not eligible:
            return None
        return min(
            eligible,
            key=lambda candidate: (
                abs((prediction.ts - candidate.ts).total_seconds()),
                candidate.ts,
            ),
        )

    def _confirm(self, sensor: SensorPrediction, video: VideoPrediction) -> HAREvent:
        timestamp = max(sensor.ts, video.ts)
        correlation_ms = abs((sensor.ts - video.ts).total_seconds()) * 1000.0
        event = HAREvent(
            ts=timestamp,
            type=EventType.FALL,
            severity=EventSeverity.CRITICAL,
            confidence=min(sensor.confidence, video.confidence),
            evidence={
                "rule": "motion_spike_and_horizontal",
                "two_modality_confirmed": True,
                "correlation_ms": correlation_ms,
                "sensor": {
                    "ts": _iso(sensor.ts),
                    "label": str(sensor.label),
                    "confidence": sensor.confidence,
                    "motion_intensity": sensor.motion_intensity,
                },
                "video": {
                    "ts": _iso(video.ts),
                    "label": str(video.label),
                    "confidence": video.confidence,
                    "orientation": str(video.orientation),
                },
                "thresholds": {
                    "fall_accel_threshold": self.fall_accel_threshold,
                    "fall_correlation_ms": self.fall_correlation_ms,
                    "fall_cooldown_seconds": self.fall_cooldown_seconds,
                    "fall_recovery_timeout_seconds": self.fall_recovery_timeout_seconds,
                    "recovery_motion_threshold": self.recovery_motion_threshold,
                },
            },
        )
        self._armed = False
        self._last_event_ts = timestamp
        self._low_motion_recovered = False
        self._upright_recovered = False
        self._spikes.clear()
        self._horizontal.clear()
        return event


class InactivityDetector:
    """Raise one inactivity event for continuous, sensor-confirmed rest."""

    _REST_LABELS = frozenset({ActivityLabel.SITTING, ActivityLabel.STANDING, ActivityLabel.LYING})

    def __init__(self, *, inactivity_seconds: float, inactivity_motion_threshold: float) -> None:
        self.inactivity_seconds = _positive("inactivity_seconds", inactivity_seconds)
        self.inactivity_motion_threshold = _positive(
            "inactivity_motion_threshold", inactivity_motion_threshold, allow_zero=True
        )
        self._still_since: datetime | None = None
        self._last_ts: datetime | None = None
        self._raised = False

    def process(self, activity: FusedActivity, sensor: SensorPrediction | None) -> HAREvent | None:
        if not isinstance(activity, FusedActivity):
            raise TypeError("activity must be FusedActivity")
        if sensor is not None and not isinstance(sensor, SensorPrediction):
            raise TypeError("sensor must be SensorPrediction or None")

        # Missing motion evidence must not accumulate time into a later alert.
        if sensor is None:
            self.reset()
            return None
        timestamp = max(activity.ts, sensor.ts)
        if self._last_ts is not None and timestamp < self._last_ts:
            return None
        self._last_ts = timestamp

        resting = activity.activity in self._REST_LABELS
        low_motion = sensor.motion_intensity <= self.inactivity_motion_threshold
        if not resting or not low_motion:
            self.reset(keep_last_timestamp=True)
            return None
        if self._still_since is None:
            self._still_since = timestamp
            return None
        duration = (timestamp - self._still_since).total_seconds()
        if self._raised or duration < self.inactivity_seconds:
            return None

        self._raised = True
        return HAREvent(
            ts=timestamp,
            type=EventType.INACTIVITY,
            severity=EventSeverity.WARNING,
            confidence=min(activity.confidence, sensor.confidence),
            evidence={
                "rule": "continuous_low_motion_rest",
                "start_ts": _iso(self._still_since),
                "duration_seconds": duration,
                "activity": str(activity.activity),
                "motion_intensity": sensor.motion_intensity,
                "thresholds": {
                    "inactivity_seconds": self.inactivity_seconds,
                    "inactivity_motion_threshold": self.inactivity_motion_threshold,
                },
            },
        )

    def reset(self, *, keep_last_timestamp: bool = False) -> None:
        self._still_since = None
        self._raised = False
        if not keep_last_timestamp:
            self._last_ts = None


class AbnormalPatternDetector:
    """Flag an unusually long activity run against its recent completed runs.

    For each activity label, the baseline is the median duration of the last
    ``abnormal_baseline_samples`` completed runs.  A current run is abnormal
    once it exceeds both the absolute minimum and median-times-multiplier.
    """

    def __init__(
        self,
        *,
        abnormal_min_seconds: float,
        abnormal_baseline_samples: int,
        abnormal_baseline_multiplier: float,
    ) -> None:
        self.abnormal_min_seconds = _positive("abnormal_min_seconds", abnormal_min_seconds)
        if (
            isinstance(abnormal_baseline_samples, bool)
            or not isinstance(abnormal_baseline_samples, int)
            or abnormal_baseline_samples < 1
        ):
            raise ValueError("abnormal_baseline_samples must be a positive integer")
        self.abnormal_baseline_samples = int(abnormal_baseline_samples)
        self.abnormal_baseline_multiplier = _positive(
            "abnormal_baseline_multiplier", abnormal_baseline_multiplier
        )
        self._baselines: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.abnormal_baseline_samples)
        )
        self._label: str | None = None
        self._run_start: datetime | None = None
        self._last_ts: datetime | None = None
        self._raised_for_run = False

    def process(self, activity: FusedActivity) -> HAREvent | None:
        if not isinstance(activity, FusedActivity):
            raise TypeError("activity must be FusedActivity")
        if self._last_ts is not None and activity.ts < self._last_ts:
            return None
        self._last_ts = activity.ts
        label = str(activity.activity)

        if self._label is None:
            self._start_run(label, activity.ts)
            return None
        if label != self._label:
            self._complete_run(activity.ts)
            self._start_run(label, activity.ts)
            return None
        if self._raised_for_run or self._run_start is None or label == ActivityLabel.UNKNOWN:
            return None

        baseline = list(self._baselines[label])
        if len(baseline) < self.abnormal_baseline_samples:
            return None
        baseline_median = float(median(baseline))
        threshold = max(
            self.abnormal_min_seconds,
            baseline_median * self.abnormal_baseline_multiplier,
        )
        duration = (activity.ts - self._run_start).total_seconds()
        if duration < threshold:
            return None

        self._raised_for_run = True
        return HAREvent(
            ts=activity.ts,
            type=EventType.ABNORMAL_PATTERN,
            severity=EventSeverity.WARNING,
            confidence=activity.confidence,
            evidence={
                "rule": "run_duration_exceeds_recent_median",
                "activity": label,
                "run_start_ts": _iso(self._run_start),
                "duration_seconds": duration,
                "completed_run_durations_seconds": baseline,
                "baseline_median_seconds": baseline_median,
                "threshold_seconds": threshold,
                "thresholds": {
                    "abnormal_min_seconds": self.abnormal_min_seconds,
                    "abnormal_baseline_samples": self.abnormal_baseline_samples,
                    "abnormal_baseline_multiplier": self.abnormal_baseline_multiplier,
                },
            },
        )

    def _complete_run(self, end: datetime) -> None:
        if self._label is None or self._run_start is None or self._label == ActivityLabel.UNKNOWN:
            return
        duration = (end - self._run_start).total_seconds()
        if duration > 0.0:
            self._baselines[self._label].append(duration)

    def _start_run(self, label: str, timestamp: datetime) -> None:
        self._label = label
        self._run_start = timestamp
        self._raised_for_run = False


class SafetyEngine:
    """Convenience facade used by the fusion runtime."""

    def __init__(
        self,
        *,
        fall_accel_threshold: float,
        fall_correlation_ms: float,
        fall_cooldown_seconds: float,
        fall_recovery_timeout_seconds: float,
        inactivity_seconds: float,
        inactivity_motion_threshold: float,
        abnormal_min_seconds: float,
        abnormal_baseline_samples: int,
        abnormal_baseline_multiplier: float,
    ) -> None:
        self.falls = FallDetector(
            fall_accel_threshold=fall_accel_threshold,
            fall_correlation_ms=fall_correlation_ms,
            fall_cooldown_seconds=fall_cooldown_seconds,
            fall_recovery_timeout_seconds=fall_recovery_timeout_seconds,
            inactivity_motion_threshold=inactivity_motion_threshold,
        )
        self.inactivity = InactivityDetector(
            inactivity_seconds=inactivity_seconds,
            inactivity_motion_threshold=inactivity_motion_threshold,
        )
        self.abnormal = AbnormalPatternDetector(
            abnormal_min_seconds=abnormal_min_seconds,
            abnormal_baseline_samples=abnormal_baseline_samples,
            abnormal_baseline_multiplier=abnormal_baseline_multiplier,
        )

    def process_prediction(self, prediction: Prediction) -> tuple[HAREvent, ...]:
        event = self.falls.process(prediction)
        return (event,) if event is not None else ()

    def process_activity(
        self, activity: FusedActivity, sensor: SensorPrediction | None
    ) -> tuple[HAREvent, ...]:
        events = (
            self.inactivity.process(activity, sensor),
            self.abnormal.process(activity),
        )
        return tuple(event for event in events if event is not None)
