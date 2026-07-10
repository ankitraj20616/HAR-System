"""Real-time, controllable replay of labelled public IMU datasets over MQTT."""

from __future__ import annotations

import argparse
import fnmatch
import json
import signal
import threading
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import paho.mqtt.client as mqtt

from shared.logging import configure_logging
from shared.schemas import SensorRaw, SensorWindow
from shared.topics import SENSOR_RAW, policy_for
from simulator.datasets import DatasetLoader, load_dataset


class Publisher(Protocol):
    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> Any: ...


class Clock(Protocol):
    def monotonic(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...

    def utcnow(self) -> datetime: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def utcnow(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class GroundTruthRecord:
    """Evaluation-only metadata, never included in a prediction/raw payload."""

    ts: str
    device_id: str
    sequence: int
    scenario_id: str
    source_label: str
    canonical_label: str


class GroundTruthSink(Protocol):
    def write(self, record: GroundTruthRecord) -> None: ...


class JsonlGroundTruthSink:
    """Append ground truth to a dedicated metrics JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, record: GroundTruthRecord) -> None:
        line = json.dumps(asdict(record), separators=(",", ":"), allow_nan=False)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


@dataclass(frozen=True, slots=True)
class ReplayOptions:
    device_id: str = "sim-01"
    realtime: bool = True
    speed: float = 1.0
    loop: bool = False
    scenario_filter: str | None = None

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise ValueError("device_id cannot be empty")
        if not 0 < self.speed <= 1000:
            raise ValueError("speed must be greater than 0 and at most 1000")
        if self.scenario_filter is not None and not self.scenario_filter.strip():
            raise ValueError("scenario_filter cannot be blank")


@dataclass(frozen=True, slots=True)
class ReplayStats:
    published: int
    completed_loops: int
    stopped: bool


class ReplayControl:
    """Thread-safe stop/pause state shared by a replay and its owner."""

    def __init__(self) -> None:
        self._stopped = threading.Event()
        self._paused = threading.Event()

    @property
    def stopped(self) -> bool:
        return self._stopped.is_set()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def stop(self) -> None:
        self._stopped.set()
        self._paused.clear()

    def pause(self) -> None:
        if not self.stopped:
            self._paused.set()

    def resume(self) -> None:
        self._paused.clear()


class ReplayEngine:
    """Publish dataset windows with monotonic pacing and separate ground truth."""

    def __init__(
        self,
        dataset: DatasetLoader,
        publisher: Publisher,
        *,
        options: ReplayOptions | None = None,
        ground_truth_sink: GroundTruthSink | None = None,
        clock: Clock | None = None,
        control: ReplayControl | None = None,
    ) -> None:
        self.dataset = dataset
        self.publisher = publisher
        self.options = options or ReplayOptions()
        self.ground_truth_sink = ground_truth_sink
        self.clock = clock or SystemClock()
        self.control = control or ReplayControl()

    def run(self) -> ReplayStats:
        published = 0
        completed_loops = 0
        while not self.control.stopped:
            emitted_this_loop = 0
            source_start: datetime | None = None
            last_source_timestamp: datetime | None = None
            previous_stream_id: str | None = None
            pacing_start = self.clock.monotonic()
            for window in self.dataset:
                if self.control.stopped:
                    break
                if not self._selected(window.scenario_id):
                    previous_stream_id = None
                    continue
                if last_source_timestamp is not None and window.timestamp < last_source_timestamp:
                    raise ValueError("dataset timestamps must be non-decreasing")
                source_start = source_start or window.timestamp
                last_source_timestamp = window.timestamp
                target = pacing_start + (
                    (window.timestamp - source_start).total_seconds() / self.options.speed
                )
                if self.options.realtime and not self._wait_until(target):
                    break
                if self.control.stopped:
                    break
                message_ts = self.clock.utcnow()
                same_stream = (
                    previous_stream_id is not None
                    and window.stream_id is not None
                    and window.stream_id == previous_stream_id
                )
                sample_start = len(window.accel) - window.stride if same_stream else 0
                message = SensorRaw(
                    ts=message_ts,
                    device_id=self.options.device_id,
                    sampling_hz=window.sampling_hz,
                    window=SensorWindow(
                        accel=list(window.accel[sample_start:]),
                        gyro=list(window.gyro[sample_start:]),
                    ),
                )
                policy = policy_for(SENSOR_RAW)
                self.publisher.publish(
                    policy.topic,
                    message.model_dump_json(),
                    qos=policy.qos,
                    retain=policy.retain,
                )
                if self.ground_truth_sink is not None:
                    self.ground_truth_sink.write(
                        GroundTruthRecord(
                            ts=message_ts.isoformat().replace("+00:00", "Z"),
                            device_id=self.options.device_id,
                            sequence=published,
                            scenario_id=window.scenario_id,
                            source_label=window.source_label,
                            canonical_label=window.canonical_label.value,
                        )
                    )
                published += 1
                emitted_this_loop += 1
                previous_stream_id = window.stream_id
            if self.control.stopped:
                break
            completed_loops += 1
            if not self.options.loop or emitted_this_loop == 0:
                break
        return ReplayStats(
            published=published,
            completed_loops=completed_loops,
            stopped=self.control.stopped,
        )

    def _selected(self, scenario_id: str) -> bool:
        pattern = self.options.scenario_filter
        return pattern is None or fnmatch.fnmatchcase(scenario_id, pattern)

    def _wait_until(self, target: float) -> bool:
        """Wait interruptibly, extending the deadline by time spent paused."""

        while not self.control.stopped:
            if self.control.paused:
                pause_started = self.clock.monotonic()
                while self.control.paused and not self.control.stopped:
                    self.clock.sleep(0.05)
                target += self.clock.monotonic() - pause_started
                continue
            remaining = target - self.clock.monotonic()
            if remaining <= 0:
                return True
            self.clock.sleep(min(remaining, 0.05))
        return False


class ReplayRunner:
    """Background lifecycle wrapper suitable for an admin/API process."""

    def __init__(self, engine: ReplayEngine) -> None:
        self.engine = engine
        self._thread: threading.Thread | None = None
        self.stats: ReplayStats | None = None
        self.error: BaseException | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            raise RuntimeError("replay is already running")
        if self.engine.control.stopped:
            raise RuntimeError("a stopped replay engine cannot be restarted")
        self._thread = threading.Thread(target=self._run, name="sensor-replay", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self.stats = self.engine.run()
        except BaseException as exc:  # preserve background failures for join()
            self.error = exc

    def pause(self) -> None:
        self.engine.control.pause()

    def resume(self) -> None:
        self.engine.control.resume()

    def stop(self) -> None:
        self.engine.control.stop()

    def join(self, timeout: float | None = None) -> ReplayStats | None:
        if self._thread is None:
            return self.stats
        self._thread.join(timeout)
        if not self._thread.is_alive() and self.error is not None:
            raise self.error
        return self.stats


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="uci-har", choices=("uci-har", "wisdm", "sisfall"))
    parser.add_argument(
        "--dataset-path",
        default=Path("data/UCI HAR Dataset"),
        type=Path,
        help="dataset root (defaults to data/UCI HAR Dataset)",
    )
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", default=1883, type=int)
    parser.add_argument("--device-id", default="sim-01")
    parser.add_argument("--speed", default=1.0, type=float)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--scenario", dest="scenario_filter")
    parser.add_argument("--ground-truth-file", type=Path)
    parser.add_argument(
        "--skip-malformed",
        action="store_true",
        help="skip malformed WISDM/SisFall rows instead of stopping",
    )
    pacing = parser.add_mutually_exclusive_group()
    pacing.add_argument("--realtime", action="store_true", default=True)
    pacing.add_argument("--no-realtime", action="store_false", dest="realtime")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logger = configure_logging("simulator")
    loader_options = {} if args.dataset == "uci-har" else {"strict": not args.skip_malformed}
    dataset = load_dataset(args.dataset, args.dataset_path, **loader_options)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"har-{args.device_id}")
    client.connect(args.mqtt_host, args.mqtt_port)
    client.loop_start()
    options = ReplayOptions(
        device_id=args.device_id,
        realtime=args.realtime,
        speed=args.speed,
        loop=args.loop,
        scenario_filter=args.scenario_filter,
    )
    sink = JsonlGroundTruthSink(args.ground_truth_file) if args.ground_truth_file else None
    engine = ReplayEngine(dataset, client, options=options, ground_truth_sink=sink)

    def stop(_signum: int, _frame: object) -> None:
        engine.control.stop()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        stats = engine.run()
        logger.info(
            "sensor replay completed",
            extra={"event": "replay_complete", "published": stats.published},
        )
    finally:
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
