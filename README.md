# HAR System

A software-only, privacy-first Human Activity Recognition system for patient monitoring. Milestone 3
adds confidence-weighted, time-aligned fusion, temporal smoothing, two-signal fall safety logic,
inactivity/abnormal-pattern safeguards, PostgreSQL timeline/event history, and live REST/WebSocket
interfaces. Raw camera frames are never stored or transmitted.

## Start everything with one command

Prerequisites: Docker Engine with Docker Compose v2 and at least 8 GB RAM. Live webcam passthrough
through Compose is supported on Linux; other platforms should run the video service on the host.

```bash
docker compose up --build --wait
```

No `.env` file is required for local development. To change ports or configuration, copy the example
and edit only the values you need:

```bash
cp .env.example .env
docker compose up --build --wait
```

Open the dashboard placeholder at <http://localhost:5173>. Inspect the runtime with:

```bash
docker compose ps
docker compose logs -f
```

Stop containers without deleting database history:

```bash
docker compose down
```

To intentionally erase local PostgreSQL and Mosquitto data, use `docker compose down --volumes`.

The default stack remains healthy when no webcam or sensor model is available: the affected service
reports `degraded`, video keeps retrying, and sensor inference uses the configured deterministic
fallback. For a Linux webcam demo, use the optional device overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.webcam.yml up --build --wait
```

Set `VIDEO_DEVICE` and `VIDEO_GID` if the camera is not `/dev/video0` or its host group is not `44`.

## Replay a public sensor dataset

UCI HAR is the default loader; WISDM and SisFall loader paths are also implemented. Dataset labels
are evaluation-only metadata and are never placed in `har/sensor/raw`:

```bash
python -m simulator.replay --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" --realtime --speed 1 \
  --ground-truth-file data/metrics/ground-truth.jsonl
```

Use `--loop`, `--scenario GLOB`, `--device-id`, `--no-realtime`, or `--skip-malformed` as needed.
The programmatic `ReplayRunner` additionally supports start, pause, resume, and stop controls.

## Optional pinned sensor model

The sensor adapter targets `STMicroelectronics/IGN-HAR-model` at revision
`69f07d89b9520c9ab4424fafed6d079c3d12b26d`. The model card specifies FLOAT32 accelerometer input
shaped `[1, window, 3, 1]`, gravity preprocessing, and the SLA0044 license. Review that license before
using the artifact. The application deliberately performs no model download at runtime.

To enable local inference, place an exact `.tflite` artifact under `data/models/`, then configure:

```dotenv
SENSOR_MODEL_PATH=/models/your-pinned-model.tflite
SENSOR_MODEL_LABELS=STATIONARY,WALKING,EXERCISING,STAIRS
USE_FALLBACK=true
```

`SENSOR_MODEL_LABELS` must match the artifact output order. Ambiguous/unmapped labels become
`UNKNOWN`; `STAIRS` maps to `WALKING`, while biking/jogging map to `EXERCISING`.

## Services and ports

| Component | Local address | Purpose |
|---|---|---|
| Dashboard | <http://localhost:5173> | Milestone 1 readiness page |
| Fusion service | <http://localhost:8001/health> | Fused activity, safety events, history, and database/MQTT health |
| Feedback service | <http://localhost:8002/health> | Feedback API skeleton and database/MQTT health |
| Sensor service | <http://localhost:8003/health> | Window/features/model-fallback inference and MQTT health |
| Video service | <http://localhost:8004/health> | Webcam/pose/activity rules and MQTT/camera health |
| Mosquitto | `localhost:1883` | MQTT message broker |
| PostgreSQL | `localhost:5432` | Timeline, events, and feedback persistence |

Container-to-container addresses are fixed (`mosquitto:1883` and `postgres:5432`). Values in
`.env` change only host-facing ports and documented application settings. Host ports bind to
`127.0.0.1` by default. Milestone 1 allows anonymous MQTT access for laptop-only development; do not
change `HOST_BIND_ADDRESS` to a public interface without first configuring authentication and TLS.

## Verify the foundation

The smoke script builds the stack, waits for health checks, verifies every HTTP endpoint, performs an
MQTT publish/subscribe round trip, and checks that all three database tables exist:

```bash
./scripts/smoke.sh
```

It stops the stack afterward but preserves named volumes. Set `SMOKE_KEEP_RUNNING=true` to leave it
running after verification.

For local Python development (Python 3.11 or 3.12):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
pytest
```

Alternatively, `uv sync --frozen` installs the same pinned runtime and development dependencies from
`uv.lock`.

CI runs the same formatting, lint, and test checks and also validates and builds every Compose image.
The Milestone 2 suite covers dataset parsing/replay, feature formulas, window overlap, local-model
adapters, MQTT contracts, synthetic postures/motion, camera lifecycle, and a privacy audit.

## Fusion API

The Fusion service exposes `GET /api/status`, `GET /api/timeline?from=&to=`,
`GET /api/trends?period=`, `GET /api/events?from=&to=`, and idempotent
`POST /api/events/{id}/ack`. The `/ws` endpoint sends typed `{channel, data}` activity and event
envelopes. Timeline/event writes are database-authoritative; MQTT and WebSocket delivery is
best-effort and retried for transient database failures. A fall requires both a sensor motion spike
and horizontal video evidence inside the configured correlation window; a single modality cannot
raise a critical fall.

## Configuration

All configuration is environment-driven. [.env.example](.env.example) documents safe development
defaults for service ports, logging, schema version, sensor windows/model preprocessing, video
thresholds and reconnect backoff, fusion weights/alignment/smoothing/safety thresholds, and
feedback-provider selection. Secrets must be supplied only through an untracked `.env` or another
secret manager. The default feedback provider is a deterministic offline template and needs no API
key.

## Repository map

```text
services/       Four FastAPI backend services
shared/         Canonical labels, topics, schemas, configuration, logging, and database helpers
simulator/      UCI HAR/WISDM/SisFall loaders and real-time MQTT replay
dashboard/      Milestone 1 health-capable dashboard placeholder
mosquitto/      Local broker configuration
tests/          Unit, contract, and integration tests
core_docs/      Functional and technical specifications plus milestone plans
```

See [Milestone 3 FSD](core_docs/milestones/milestone-3-fusion-safety/FSD.md),
[Milestone 3 TDD](core_docs/milestones/milestone-3-fusion-safety/TDD.md),
[Milestone 2 FSD](core_docs/milestones/milestone-2-single-modality/FSD.md),
[Milestone 2 TDD](core_docs/milestones/milestone-2-single-modality/TDD.md), and
[Milestone 2 implementation notes](core_docs/milestones/milestone-2-single-modality/IMPLEMENTATION.md)
for scope and acceptance criteria. Fusion-ready fixtures are in
`tests/fixtures/milestone2_predictions.json`.

## Privacy and safety

- Raw camera frames must never be stored, encoded, logged, or published; only numeric prediction
  contracts leave the video service.
- Logs must not contain full sensor windows, frames, secrets, or API keys.
- This academic prototype is an assistive tool, not a medical device or diagnosis system.
- Dataset files and model weights belong under `data/`, which is intentionally ignored by Git.
