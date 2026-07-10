# Sensor Dataset Simulator

The simulator makes a public activity dataset behave like a live wearable motion sensor. It reads
accelerometer and gyroscope samples, creates valid `SensorRaw` messages, and publishes them to MQTT
topic `har/sensor/raw`.

This lets the full HAR pipeline run without buying or wiring physical sensor hardware.

## What the simulator does

For each dataset window, the simulator:

1. reads numeric accelerometer and gyroscope samples;
2. converts source units to the units expected by the Sensor Service;
3. assigns a fresh current UTC message timestamp;
4. publishes the strict shared JSON contract to Mosquitto;
5. optionally writes the known dataset label to a separate ground-truth JSONL file.

The expected label is **never** added to the MQTT sensor message. This prevents the recognition
pipeline from seeing the correct answer during evaluation.

## Supported datasets

| Dataset | Accepted input | Default sample rate | Important behavior |
|---|---|---:|---|
| UCI HAR | Standard extracted `UCI HAR Dataset` directory | 50 Hz | Reads provided 128-sample inertial windows |
| WISDM | Raw `.txt`/`.csv` rows: `user,label,timestamp,x,y,z` | 20 Hz | Builds 128-sample windows; gyro is zero because the source is accelerometer-only |
| SisFall | Extracted scenario files such as `D01_*.txt` and `F01_*.txt` | 200 Hz | Reads daily-activity and fall scenarios recursively |

Dataset files are not included in Git. Put downloaded/extracted files under `data/`.

## Before running a replay

Mosquitto must be reachable. The Sensor Service should also be running if you want raw data to become
predictions, and the Fusion Service should be running if you want final activity/history.

The easiest option is to start the full project:

```bash
docker compose up --build --wait
```

For local Python usage, activate the project environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

## Basic UCI HAR replay

Expected directory example:

```text
data/
  UCI HAR Dataset/
    activity_labels.txt
    train/
      Inertial Signals/
      subject_train.txt
      y_train.txt
    test/
      Inertial Signals/
      subject_test.txt
      y_test.txt
```

Run the dataset at its normal recorded timing:

```bash
python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --realtime \
  --speed 1
```

The loader also accepts a parent directory containing a nested `UCI HAR Dataset/` folder.

## WISDM replay

The loader accepts either the raw WISDM file or a directory. When a directory is supplied, it uses
the first sorted `.txt` or `.csv` file.

Expected row format:

```text
user,label,timestamp,x,y,z
```

Example:

```bash
python -m simulator.replay \
  --dataset wisdm \
  --dataset-path data/WISDM/WISDM_ar_v1.1_raw.txt \
  --realtime \
  --speed 1
```

WISDM accelerometer values are converted from `m/s²` to `g`. Because this source does not contain a
gyroscope channel, the loader supplies zero gyro samples. A new stream segment starts whenever the
user or activity label changes.

## SisFall replay

Pass the extracted SisFall root. The loader searches subdirectories recursively for `.txt` and
`.csv` scenario files whose names start with `D` (daily activity) or `F` (fall).

Example directory:

```text
data/
  SisFall_dataset/
    SA01/
      D01_SA01_R01.txt
      F01_SA01_R01.txt
    SE01/
      D01_SE01_R01.txt
```

Replay every scenario:

```bash
python -m simulator.replay \
  --dataset sisfall \
  --dataset-path data/SisFall_dataset \
  --realtime \
  --speed 1
```

Replay only fall scenarios:

```bash
python -m simulator.replay \
  --dataset sisfall \
  --dataset-path data/SisFall_dataset \
  --scenario 'F*' \
  --speed 5
```

SisFall accelerometer counts are divided by `256` to produce `g`. Gyroscope counts are converted to
`rad/s`. A fall source label is evaluation metadata and maps to activity `UNKNOWN`; the actual `FALL`
event must still be detected downstream from sensor motion plus horizontal video evidence.

## Command options

Show the built-in help:

```bash
python -m simulator.replay --help
```

| Option | Default | Meaning |
|---|---|---|
| `--dataset` | `uci-har` | Choose `uci-har`, `wisdm`, or `sisfall` |
| `--dataset-path` | `data/UCI HAR Dataset` | File or extracted dataset root |
| `--mqtt-host` | `localhost` | Mosquitto hostname |
| `--mqtt-port` | `1883` | Mosquitto port |
| `--device-id` | `sim-01` | Device ID placed in each raw message |
| `--speed` | `1.0` | Replay multiplier; must be greater than 0 and at most 1000 |
| `--loop` | off | Start again after reaching the end |
| `--scenario` | all | Unix-style scenario filter such as `'F*'` or `'uci-test-subject-02-*'` |
| `--ground-truth-file` | off | Append evaluation metadata to a JSONL file |
| `--skip-malformed` | off | Skip bad WISDM/SisFall rows instead of stopping |
| `--realtime` | on | Preserve source timing divided by `--speed` |
| `--no-realtime` | off | Publish as quickly as possible |

Quote wildcard patterns so the shell does not expand them before the simulator sees them.

## Useful replay examples

### Replay ten times faster

```bash
python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --speed 10
```

### Publish as fast as possible

```bash
python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --no-realtime
```

### Repeat until interrupted

```bash
python -m simulator.replay \
  --dataset wisdm \
  --dataset-path data/WISDM/raw.txt \
  --loop
```

Press `Ctrl+C` for a graceful stop.

### Use a different broker

```bash
python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --mqtt-host 192.168.1.20 \
  --mqtt-port 1883 \
  --device-id room-01-simulator
```

Do not send unencrypted anonymous MQTT traffic over an untrusted network.

## Ground-truth output

Write evaluation labels separately:

```bash
python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --ground-truth-file data/metrics/ground-truth.jsonl
```

Each JSONL line contains fields similar to:

```json
{
  "ts": "2026-07-10T10:00:00Z",
  "device_id": "sim-01",
  "sequence": 0,
  "scenario_id": "uci-train-subject-01-window-000001",
  "source_label": "STANDING",
  "canonical_label": "STANDING"
}
```

This file is intended for later F1, precision, recall, and latency measurement. It is not published
to `har/sensor/raw`.

## MQTT message shape

The simulator publishes a versioned `SensorRaw` message:

```json
{
  "schema_version": "1.0",
  "ts": "2026-07-10T10:00:00Z",
  "device_id": "sim-01",
  "sampling_hz": 50.0,
  "window": {
    "accel": [[0.1, 0.0, 1.0]],
    "gyro": [[0.0, 0.01, 0.0]]
  }
}
```

Real messages contain many samples. Both channels must be non-empty and have the same number of
three-value vectors. The strict shared schema rejects invalid timestamps, non-finite values, unequal
channel lengths, and unknown fields.

## Window and overlap behavior

The source loaders produce 128-sample windows with a 64-sample stride by default.

- The first message of a continuous stream contains the full warm-up window.
- Later overlapping source windows publish only their new stride samples.
- The Sensor Service's own sliding buffer reconstructs the correct next window.

This prevents overlapped dataset samples from being counted twice downstream.

When a scenario, subject stream, user, or activity segment changes, the next message starts with a
full window again.

## Timing behavior

Replay pacing uses a monotonic clock, so system-clock adjustments do not create a negative sleep or
time jump. MQTT messages still receive a fresh UTC wall-clock timestamp for cross-service alignment.

`--speed 2` means half the normal waiting time. `--speed 10` means one tenth. `--no-realtime` removes
the wait completely but still preserves message order.

## Programmatic controls

Code that embeds the simulator can use `ReplayEngine`, `ReplayControl`, and `ReplayRunner`.

`ReplayRunner` runs the engine on a background thread and provides:

- `start()` — begin replay;
- `pause()` — temporarily stop publishing without losing position;
- `resume()` — continue and adjust pacing for the paused duration;
- `stop()` — request a clean stop;
- `join(timeout)` — wait for completion and receive replay statistics.

A stopped engine cannot be restarted. Create a new engine for a new replay session.

## Label mapping

Dataset labels are converted to the fixed project vocabulary. Common examples:

| Source label | Canonical activity |
|---|---|
| `WALKING`, `WALKING_UPSTAIRS`, `WALKING_DOWNSTAIRS`, `STAIRS` | `WALKING` |
| `SITTING`, `SIT` | `SITTING` |
| `STANDING`, `STAND` | `STANDING` |
| `LAYING`, `LYING`, `LIE` | `LYING` |
| `JOGGING`, `RUNNING`, `BIKING` | `EXERCISING` |
| unrecognized labels and fall scenario labels | `UNKNOWN` |

`FALL` is an event, not a normal activity label.

## Invalid data behavior

UCI HAR structural errors always stop the loader because its split files must stay aligned.

WISDM and SisFall are strict by default. A malformed row stops replay with a path and line number.
For exploratory runs, add:

```bash
--skip-malformed
```

Bad rows are then ignored. If too few valid samples remain to make a complete window, that section
produces no message.

## Troubleshooting

### Connection refused

Mosquitto is not reachable at the selected host/port. Check:

```bash
docker compose ps mosquitto
docker compose logs mosquitto
```

If the simulator runs inside a container, `localhost` means that container. Use the Compose service
hostname `mosquitto` there.

### Dataset path does not exist

Confirm extraction and spelling:

```bash
find data -maxdepth 3 -type f | head
```

For UCI HAR, the folder must contain `activity_labels.txt`, `train/`, and `test/`.

### Replay publishes zero messages

- the `--scenario` pattern may match nothing;
- WISDM/SisFall may not have 128 valid consecutive samples;
- a directory may not contain a supported file extension;
- malformed rows may all be skipped.

### Sensor Service receives data but publishes no prediction

The service needs enough samples to fill its configured window. Check `WINDOW_SIZE`, simulator logs,
Sensor Service logs, and model/fallback health.

### Replay is too slow or too fast

Use `--speed` while keeping real-time order, or `--no-realtime` for a fast test. Very high rates can
fill downstream queues, so use realistic pacing for latency demonstrations.

## Tests

Run simulator tests only:

```bash
pytest tests/unit/test_simulator_datasets.py tests/unit/test_simulator_replay.py
```

Run the sensor-flow integration test:

```bash
pytest tests/integration/test_simulator_sensor_flow.py
```

Downloaded datasets are not required for the automated unit suite; tests use small synthetic
fixtures.

## Privacy and evaluation rules

- Store downloaded datasets and generated metrics under `data/`.
- Do not commit dataset files, patient-like recordings, or model weights.
- Do not place ground truth in MQTT inference messages.
- Do not log complete raw sensor windows in normal service logs.
- Treat public dataset licenses and citation requirements separately from this repository's code.
