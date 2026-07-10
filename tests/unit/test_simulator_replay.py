from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from shared.schemas import SensorRaw
from shared.topics import SENSOR_RAW
from simulator.datasets import DatasetWindow
from simulator.replay import (
    GroundTruthRecord,
    JsonlGroundTruthSink,
    ReplayControl,
    ReplayEngine,
    ReplayOptions,
    ReplayRunner,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []
        self.origin = datetime(2026, 1, 1, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds

    def utcnow(self) -> datetime:
        return self.origin + timedelta(seconds=self.value)


@dataclass
class CollectingSink:
    records: list[GroundTruthRecord]

    def write(self, record: GroundTruthRecord) -> None:
        self.records.append(record)


class CollectingPublisher:
    def __init__(self, stop_after: int | None = None, control: ReplayControl | None = None) -> None:
        self.messages: list[tuple[str, str, int, bool]] = []
        self.stop_after = stop_after
        self.control = control

    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> Any:
        self.messages.append((topic, payload, qos, retain))
        if self.stop_after is not None and len(self.messages) >= self.stop_after:
            assert self.control is not None
            self.control.stop()
        return None


def _window(offset: float, scenario: str = "scenario-1", label: str = "WALKING") -> DatasetWindow:
    sample = ((1.0, 2.0, 3.0),)
    return DatasetWindow(
        timestamp=datetime(2020, 1, 1, tzinfo=UTC) + timedelta(seconds=offset),
        sampling_hz=50.0,
        accel=sample,
        gyro=sample,
        source_label=label,
        scenario_id=scenario,
    )


def test_replay_paces_with_monotonic_clock_and_speed_factor() -> None:
    clock = FakeClock()
    publisher = CollectingPublisher()
    engine = ReplayEngine(
        [_window(0), _window(1), _window(2)],  # type: ignore[arg-type]
        publisher,
        options=ReplayOptions(speed=2.0),
        clock=clock,
    )

    stats = engine.run()

    assert stats.published == 3
    assert clock.value == pytest.approx(1.0)
    assert sum(clock.sleeps) == pytest.approx(1.0)
    timestamps = [SensorRaw.model_validate_json(item[1]).ts for item in publisher.messages]
    assert timestamps == sorted(timestamps)


def test_raw_payload_excludes_ground_truth_and_sink_keeps_it_separate() -> None:
    publisher = CollectingPublisher()
    sink = CollectingSink([])
    ReplayEngine(
        [_window(0, "subject-7", "LAYING")],  # type: ignore[arg-type]
        publisher,
        options=ReplayOptions(realtime=False, device_id="sim-test"),
        ground_truth_sink=sink,
        clock=FakeClock(),
    ).run()

    topic, payload, qos, retain = publisher.messages[0]
    raw = json.loads(payload)
    assert topic == SENSOR_RAW
    assert qos == 0 and retain is False
    assert "label" not in payload and "scenario" not in payload
    assert raw["device_id"] == "sim-test"
    assert sink.records[0].scenario_id == "subject-7"
    assert sink.records[0].canonical_label == "LYING"
    assert sink.records[0].ts == raw["ts"]


def test_overlapped_dataset_windows_publish_only_new_stride_samples() -> None:
    samples = tuple((float(index), 0.0, 1.0) for index in range(8))
    windows = [
        DatasetWindow(
            timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            sampling_hz=4,
            accel=samples[:6],
            gyro=((0.0, 0.0, 0.0),) * 6,
            source_label="WALKING",
            scenario_id="stream-window-1",
            stride_samples=2,
            stream_id="stream-1",
        ),
        DatasetWindow(
            timestamp=datetime(2020, 1, 1, tzinfo=UTC) + timedelta(seconds=0.5),
            sampling_hz=4,
            accel=samples[2:8],
            gyro=((0.0, 0.0, 0.0),) * 6,
            source_label="WALKING",
            scenario_id="stream-window-2",
            stride_samples=2,
            stream_id="stream-1",
        ),
    ]
    publisher = CollectingPublisher()

    ReplayEngine(
        windows,  # type: ignore[arg-type]
        publisher,
        options=ReplayOptions(realtime=False),
        clock=FakeClock(),
    ).run()

    payloads = [SensorRaw.model_validate_json(item[1]) for item in publisher.messages]
    assert [len(payload.window.accel) for payload in payloads] == [6, 2]
    assert payloads[1].window.accel == list(samples[-2:])


def test_scenario_glob_filters_without_affecting_pacing_origin() -> None:
    clock = FakeClock()
    publisher = CollectingPublisher()
    stats = ReplayEngine(
        [_window(0, "skip"), _window(20, "keep-1"), _window(21, "keep-2")],  # type: ignore[arg-type]
        publisher,
        options=ReplayOptions(speed=1, scenario_filter="keep-*"),
        clock=clock,
    ).run()

    assert stats.published == 2
    assert clock.value == pytest.approx(1.0)


def test_loop_can_be_stopped_interruptibly() -> None:
    control = ReplayControl()
    publisher = CollectingPublisher(stop_after=3, control=control)
    stats = ReplayEngine(
        [_window(0), _window(0.1)],  # type: ignore[arg-type]
        publisher,
        options=ReplayOptions(realtime=False, loop=True),
        control=control,
        clock=FakeClock(),
    ).run()

    assert stats.published == 3
    assert stats.stopped is True


def test_background_runner_exposes_start_pause_resume_and_stop() -> None:
    control = ReplayControl()
    publisher = CollectingPublisher(stop_after=1, control=control)
    runner = ReplayRunner(
        ReplayEngine(
            [_window(0)],  # type: ignore[arg-type]
            publisher,
            options=ReplayOptions(realtime=False, loop=True),
            control=control,
            clock=FakeClock(),
        )
    )

    runner.pause()
    assert control.paused is True
    runner.resume()
    runner.start()
    stats = runner.join(timeout=1)

    assert stats is not None and stats.published == 1
    assert runner.running is False
    runner.stop()


def test_jsonl_ground_truth_sink_writes_evaluation_record(tmp_path: Path) -> None:
    path = tmp_path / "metrics" / "truth.jsonl"
    record = GroundTruthRecord(
        ts="2026-01-01T00:00:00Z",
        device_id="sim-1",
        sequence=0,
        scenario_id="s1",
        source_label="Jogging",
        canonical_label="EXERCISING",
    )

    JsonlGroundTruthSink(path).write(record)

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "ts": "2026-01-01T00:00:00Z",
        "device_id": "sim-1",
        "sequence": 0,
        "scenario_id": "s1",
        "source_label": "Jogging",
        "canonical_label": "EXERCISING",
    }


@pytest.mark.parametrize("speed", [0, -1, 1001])
def test_invalid_speed_is_rejected(speed: float) -> None:
    with pytest.raises(ValueError, match="speed"):
        ReplayOptions(speed=speed)
