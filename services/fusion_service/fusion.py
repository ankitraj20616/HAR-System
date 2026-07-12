"""Time alignment, confidence-weighted fusion, and temporal smoothing.

The module deliberately contains no MQTT, database, FastAPI, or safety-event
code.  ``FusionEngine`` is thread-safe so an MQTT callback can add predictions
while an async runtime executes interval ticks.
"""

from __future__ import annotations

import math
from bisect import bisect_left, insort
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Literal

from services.fusion_service.config import FusionSettings
from shared.labels import ActivityLabel
from shared.schemas import Contributors, FusedActivity, SensorPrediction, VideoPrediction

Prediction = SensorPrediction | VideoPrediction
AddStatus = Literal["accepted", "duplicate", "late"]


def _require_utc(value: datetime, *, name: str = "timestamp") -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must use UTC")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class BufferAddResult:
    status: AddStatus
    evicted: int = 0

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    def __bool__(self) -> bool:
        return self.accepted


@dataclass(frozen=True)
class BufferSelection:
    prediction: Prediction | None
    stale_discarded: int = 0
    alignment_expired: int = 0
    superseded: int = 0


class PredictionBuffer:
    """A bounded timestamp-ordered buffer with retention-scoped deduplication."""

    def __init__(self, modality: str, *, retention: timedelta, max_size: int) -> None:
        if modality not in {"sensor", "video"}:
            raise ValueError("modality must be sensor or video")
        if retention <= timedelta(0):
            raise ValueError("retention must be positive")
        if max_size < 1:
            raise ValueError("max_size must be positive")
        self.modality = modality
        self.retention = retention
        self.max_size = max_size
        self._timestamps: list[datetime] = []
        self._predictions: dict[datetime, Prediction] = {}
        self._seen: set[datetime] = set()
        self._latest_timestamp: datetime | None = None
        self._lock = RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._timestamps)

    @property
    def latest_timestamp(self) -> datetime | None:
        with self._lock:
            return self._latest_timestamp

    @property
    def timestamps(self) -> tuple[datetime, ...]:
        """Ordered timestamp snapshot, useful for diagnostics and tests."""

        with self._lock:
            return tuple(self._timestamps)

    def add(self, prediction: Prediction) -> BufferAddResult:
        if prediction.modality != self.modality:
            raise ValueError(
                f"{self.modality} buffer cannot accept {prediction.modality} prediction"
            )
        timestamp = _require_utc(prediction.ts, name="prediction timestamp")
        with self._lock:
            if timestamp in self._seen:
                return BufferAddResult("duplicate")

            if (
                self._latest_timestamp is not None
                and timestamp < self._latest_timestamp - self.retention
            ):
                return BufferAddResult("late")

            if self._latest_timestamp is None or timestamp > self._latest_timestamp:
                self._latest_timestamp = timestamp
            self._seen.add(timestamp)
            self._predictions[timestamp] = prediction
            insort(self._timestamps, timestamp)

            evicted = self._prune_retention_locked()
            while len(self._timestamps) > self.max_size:
                self._remove_at_locked(0, forget=True)
                evicted += 1
            # Keep the dedupe set bounded even when selected entries are removed.
            if len(self._seen) > self.max_size:
                active = set(self._timestamps)
                consumed = sorted(self._seen - active)
                for old_timestamp in consumed[: len(self._seen) - self.max_size]:
                    self._seen.remove(old_timestamp)
            return BufferAddResult("accepted", evicted=evicted)

    def select_nearest(
        self,
        target: datetime,
        *,
        tolerance: timedelta,
        stale_timeout: timedelta,
    ) -> BufferSelection:
        target = _require_utc(target, name="fusion timestamp")
        if tolerance < timedelta(0):
            raise ValueError("tolerance cannot be negative")
        if stale_timeout <= timedelta(0):
            raise ValueError("stale_timeout must be positive")

        with self._lock:
            stale_cutoff = target - stale_timeout
            alignment_cutoff = target - tolerance
            stale_discarded = self._remove_before_locked(stale_cutoff, forget=True)
            alignment_expired = self._remove_before_locked(alignment_cutoff, forget=True)

            upper = target + tolerance
            upper_index = bisect_left(self._timestamps, upper)
            if upper_index < len(self._timestamps) and self._timestamps[upper_index] == upper:
                upper_index += 1
            candidates = self._timestamps[:upper_index]
            if not candidates:
                return BufferSelection(
                    prediction=None,
                    stale_discarded=stale_discarded,
                    alignment_expired=alignment_expired,
                )

            # Earlier evidence wins an exact-distance tie; this avoids looking
            # ahead when clocks straddle an interval boundary.
            chosen_timestamp = min(candidates, key=lambda ts: (abs(ts - target), ts))
            chosen_index = bisect_left(self._timestamps, chosen_timestamp)
            prediction = self._predictions[chosen_timestamp]
            superseded = chosen_index
            for _ in range(chosen_index + 1):
                # Retain selected/superseded identities for QoS-1 deduplication.
                self._remove_at_locked(0, forget=False)
            return BufferSelection(
                prediction=prediction,
                stale_discarded=stale_discarded,
                alignment_expired=alignment_expired,
                superseded=superseded,
            )

    def _prune_retention_locked(self) -> int:
        if self._latest_timestamp is None:
            return 0
        return self._remove_before_locked(
            self._latest_timestamp - self.retention,
            forget=True,
        )

    def _remove_before_locked(self, cutoff: datetime, *, forget: bool) -> int:
        count = bisect_left(self._timestamps, cutoff)
        for _ in range(count):
            self._remove_at_locked(0, forget=forget)
        return count

    def _remove_at_locked(self, index: int, *, forget: bool) -> None:
        timestamp = self._timestamps.pop(index)
        self._predictions.pop(timestamp, None)
        if forget:
            self._seen.discard(timestamp)


@dataclass(frozen=True)
class WeightedVote:
    label: ActivityLabel
    confidence: float
    scores: dict[ActivityLabel, float]
    active_weights: dict[str, float]


def confidence_weighted_vote(
    sensor: SensorPrediction | None,
    video: VideoPrediction | None,
    *,
    modality_weights: dict[str, float],
    previous_stable: ActivityLabel | None = None,
) -> WeightedVote:
    """Fuse the available predictions, normalizing weights over active sources."""

    predictions: tuple[Prediction, ...] = tuple(
        prediction for prediction in (sensor, video) if prediction is not None
    )
    if not predictions:
        raise ValueError("at least one prediction is required")

    active_names = [str(prediction.modality) for prediction in predictions]
    try:
        total_weight = sum(modality_weights[name] for name in active_names)
    except KeyError as exc:
        raise ValueError(f"missing weight for modality {exc.args[0]!r}") from exc
    if not math.isfinite(total_weight) or total_weight <= 0.0:
        raise ValueError("active modality weights must have a finite positive sum")

    active_weights = {name: modality_weights[name] / total_weight for name in active_names}
    scores: dict[ActivityLabel, float] = {}
    for prediction in predictions:
        label = ActivityLabel(prediction.label)
        contribution = active_weights[str(prediction.modality)] * float(prediction.confidence)
        scores[label] = scores.get(label, 0.0) + contribution

    winning_score = max(scores.values())
    tied = {
        label
        for label, score in scores.items()
        if math.isclose(score, winning_score, rel_tol=1e-12, abs_tol=1e-12)
    }
    if len(tied) == 1:
        winner = next(iter(tied))
    elif previous_stable is not None and previous_stable in tied:
        winner = previous_stable
    else:
        winner = ActivityLabel.UNKNOWN

    return WeightedVote(
        label=winner,
        confidence=max(0.0, min(1.0, winning_score)),
        scores=dict(sorted(scores.items(), key=lambda item: item[0].value)),
        active_weights=active_weights,
    )


@dataclass(frozen=True)
class SmoothedVote:
    raw_label: ActivityLabel
    raw_confidence: float
    stable_label: ActivityLabel
    stable_confidence: float


class TemporalSmoother:
    """Rolling majority smoother whose ties preserve the displayed label."""

    def __init__(self, window_size: int) -> None:
        if window_size < 1:
            raise ValueError("window_size must be positive")
        self.window_size = window_size
        self._history: deque[tuple[ActivityLabel, float]] = deque(maxlen=window_size)
        self._stable_label: ActivityLabel | None = None

    @property
    def stable_label(self) -> ActivityLabel | None:
        return self._stable_label

    @property
    def history(self) -> tuple[tuple[ActivityLabel, float], ...]:
        return tuple(self._history)

    def update(self, label: ActivityLabel | str, confidence: float) -> SmoothedVote:
        label = ActivityLabel(label)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be finite and between 0 and 1")
        self._history.append((label, confidence))
        counts = Counter(item[0] for item in self._history)
        largest_count = max(counts.values())
        tied = {candidate for candidate, count in counts.items() if count == largest_count}
        if len(tied) == 1:
            stable = next(iter(tied))
        elif self._stable_label is not None and self._stable_label in tied:
            stable = self._stable_label
        else:
            stable = ActivityLabel.UNKNOWN
        self._stable_label = stable
        supporting = [score for candidate, score in self._history if candidate == stable]
        stable_confidence = sum(supporting) / len(supporting) if supporting else 0.0
        return SmoothedVote(
            raw_label=label,
            raw_confidence=confidence,
            stable_label=stable,
            stable_confidence=stable_confidence,
        )


@dataclass(frozen=True)
class FusionDecision:
    activity: FusedActivity
    raw_label: ActivityLabel
    raw_confidence: float
    stable_label: ActivityLabel
    stable_confidence: float
    sensor: SensorPrediction | None
    video: VideoPrediction | None
    scores: dict[ActivityLabel, float]
    active_weights: dict[str, float]
    source_latency_seconds: float


@dataclass
class _MutableCounters:
    inputs: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    accepted: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    duplicates: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    late: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    evicted: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    stale: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    alignment_expired: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    superseded: dict[str, int] = field(default_factory=lambda: {"sensor": 0, "video": 0})
    intervals: int = 0
    empty_intervals: int = 0
    decisions: int = 0


class FusionEngine:
    """Own modality buffers and produce one stable decision per fusion tick."""

    def __init__(self, settings: FusionSettings) -> None:
        self.settings = settings
        self._buffers = {
            modality: PredictionBuffer(
                modality,
                retention=settings.buffer_retention,
                max_size=settings.buffer_max_size,
            )
            for modality in ("sensor", "video")
        }
        self._smoother = TemporalSmoother(settings.smoothing_window)
        self._counters = _MutableCounters()
        self._last_received: dict[str, datetime | None] = {"sensor": None, "video": None}
        self._last_decision: FusionDecision | None = None
        self._lock = RLock()

    def add(self, prediction: Prediction) -> BufferAddResult:
        if not isinstance(prediction, SensorPrediction | VideoPrediction):
            raise TypeError("prediction must be SensorPrediction or VideoPrediction")
        modality = str(prediction.modality)
        with self._lock:
            self._counters.inputs[modality] += 1
            result = self._buffers[modality].add(prediction)
            if result.status == "accepted":
                self._counters.accepted[modality] += 1
                received = self._last_received[modality]
                if received is None or prediction.ts > received:
                    self._last_received[modality] = prediction.ts
                self._counters.evicted[modality] += result.evicted
            elif result.status == "duplicate":
                self._counters.duplicates[modality] += 1
            else:
                self._counters.late[modality] += 1
            return result

    def fuse(self, now: datetime | None = None) -> FusionDecision | None:
        timestamp = _require_utc(now or datetime.now(UTC), name="fusion timestamp")
        with self._lock:
            self._counters.intervals += 1
            selections = {
                modality: buffer.select_nearest(
                    timestamp,
                    tolerance=self.settings.alignment_tolerance,
                    stale_timeout=self.settings.stale_timeout,
                )
                for modality, buffer in self._buffers.items()
            }
            for modality, selection in selections.items():
                self._counters.stale[modality] += selection.stale_discarded
                self._counters.alignment_expired[modality] += selection.alignment_expired
                self._counters.superseded[modality] += selection.superseded

            sensor = selections["sensor"].prediction
            video = selections["video"].prediction
            if sensor is None and video is None:
                self._counters.empty_intervals += 1
                return None
            if sensor is not None and not isinstance(sensor, SensorPrediction):
                raise RuntimeError("sensor buffer returned the wrong prediction type")
            if video is not None and not isinstance(video, VideoPrediction):
                raise RuntimeError("video buffer returned the wrong prediction type")

            # A prediction can be close to the interval boundary while its
            # counterpart is close to the opposite boundary. Do not present
            # those temporally unrelated samples as a confident two-source
            # vote; retain the source nearest the tick and continue degraded.
            if sensor is not None and video is not None:
                source_delta = abs(sensor.ts - video.ts)
                if source_delta > self.settings.alignment_tolerance:
                    sensor_distance = abs(sensor.ts - timestamp)
                    video_distance = abs(video.ts - timestamp)
                    if sensor_distance <= video_distance:
                        video = None
                    else:
                        sensor = None

            vote = confidence_weighted_vote(
                sensor,
                video,
                modality_weights=self.settings.modality_weights,
                previous_stable=self._smoother.stable_label,
            )
            smoothed = self._smoother.update(vote.label, vote.confidence)
            contributors = Contributors(
                sensor=sensor.label if sensor is not None else None,
                video=video.label if video is not None else None,
            )
            activity = FusedActivity(
                ts=timestamp,
                activity=smoothed.stable_label,
                confidence=smoothed.stable_confidence,
                contributors=contributors,
            )
            latest_source = max(
                prediction.ts for prediction in (sensor, video) if prediction is not None
            )
            decision = FusionDecision(
                activity=activity,
                raw_label=smoothed.raw_label,
                raw_confidence=smoothed.raw_confidence,
                stable_label=smoothed.stable_label,
                stable_confidence=smoothed.stable_confidence,
                sensor=sensor,
                video=video,
                scores=vote.scores,
                active_weights=vote.active_weights,
                source_latency_seconds=max(0.0, (timestamp - latest_source).total_seconds()),
            )
            self._last_decision = decision
            self._counters.decisions += 1
            return decision

    @property
    def diagnostics(self) -> dict[str, object]:
        """Return a detached snapshot safe for health/status serialization."""

        with self._lock:
            counters = self._counters
            return {
                "counters": {
                    "inputs": dict(counters.inputs),
                    "accepted": dict(counters.accepted),
                    "duplicates": dict(counters.duplicates),
                    "late": dict(counters.late),
                    "evicted": dict(counters.evicted),
                    "stale": dict(counters.stale),
                    "alignment_expired": dict(counters.alignment_expired),
                    "superseded": dict(counters.superseded),
                    "intervals": counters.intervals,
                    "empty_intervals": counters.empty_intervals,
                    "decisions": counters.decisions,
                },
                "last_received": dict(self._last_received),
                "buffer_sizes": {
                    modality: len(buffer) for modality, buffer in self._buffers.items()
                },
                "raw_label": (self._last_decision.raw_label.value if self._last_decision else None),
                "stable_label": (
                    self._last_decision.stable_label.value if self._last_decision else None
                ),
                "last_update": (self._last_decision.activity.ts if self._last_decision else None),
            }

    @property
    def last_received(self) -> dict[str, datetime | None]:
        with self._lock:
            return dict(self._last_received)

    @property
    def last_decision(self) -> FusionDecision | None:
        with self._lock:
            return self._last_decision
