# HAR System

HAR means **Human Activity Recognition**. This project watches two privacy-safe data streams and
turns them into one simple activity result:

- simulated wearable motion data, such as accelerometer and gyroscope values;
- webcam pose data, reduced immediately to body landmarks and posture information.

The system can recognize `WALKING`, `SITTING`, `STANDING`, `LYING`, `EXERCISING`, and `UNKNOWN`.
It can also create `FALL`, `INACTIVITY`, and `ABNORMAL_PATTERN` safety events.

This is a college project and an assistive monitoring prototype. It is **not a medical device**, it
does not make a diagnosis, and it must not replace a caregiver or emergency service.

## What is available now

Milestones 1 through 5 are implemented. Final target-laptop results remain `NOT RUN` until the
release runbook is executed and its evidence is reviewed.

| Area | Current state |
|---|---|
| Docker, MQTT, PostgreSQL, shared contracts, health checks | Implemented |
| UCI HAR, WISDM, and SisFall sensor replay | Implemented |
| Sensor windowing, features, local model adapter, deterministic fallback | Implemented |
| Webcam capture, MediaPipe pose landmarks, posture rules, privacy controls | Implemented |
| Time alignment, confidence-weighted fusion, temporal smoothing | Implemented |
| Fall, inactivity, and explainable abnormal-pattern detection | Implemented |
| Activity/event persistence, REST API, and WebSocket updates | Implemented |
| Caregiver dashboard, live alerts, history, trends, and health | Implemented |
| Structured Ollama feedback, summaries, safety validation, and fallback | Implemented |
| Fixed-scenario metrics harness and machine/human-readable reports | Implemented |
| Release audit, dependency pin validation, and CI release gates | Implemented |
| Demo/operations runbook and privacy/offline/usability evidence package | Implemented; target-laptop evidence pending |

Open the caregiver dashboard at <http://localhost:5173> after starting the stack.

For a one-command seeded prototype, service controls, environment-value guidance, and the complete
local walkthrough, see [LOCAL_SETUP_GUIDE.md](LOCAL_SETUP_GUIDE.md):

```bash
./dev.sh up
```

## How the system works

```text
Public sensor dataset
        |
        v
Sensor simulator --har/sensor/raw--> Sensor Service
                                         |
                                         | har/sensor/prediction
                                         v
                                      Mosquitto
                                         ^
                                         | har/video/prediction
Webcam --> numeric pose landmarks --> Video Service
                                         |
                                         v
                                  Fusion Service
                            alignment + voting + smoothing
                            fall/inactivity safety rules
                              |                    |
                              v                    v
                         PostgreSQL          MQTT + WebSocket
                     timeline and events      live consumers
```

The Fusion Service is the authoritative source. It stores a result in PostgreSQL before attempting
live MQTT and WebSocket delivery. If a live consumer is temporarily unavailable, the saved history
is still available from the REST API.

## Important safety behavior

A critical fall is created only when both of these signals agree inside the configured time window:

1. the sensor prediction contains a strong motion spike;
2. the video prediction reports a horizontal body orientation.

One signal alone cannot create a normal critical fall alert. This reduces false alarms from ordinary
lying down, exercise, camera mistakes, or sensor noise.

After a confirmed fall, cooldown and recovery rules prevent repeated alerts for the same incident.
The detector becomes ready again after upright plus low-motion recovery, or after the configured
recovery timeout.

## Requirements

For the easiest setup, install:

- Docker Engine;
- Docker Compose v2, available as `docker compose`;
- at least 8 GB RAM;
- a webcam only if you want live video recognition.

Python 3.11 or 3.12 is needed only for local development, tests, or running the simulator outside
Docker.

## Quick start with Docker

Start the complete stack from the repository root:

```bash
docker compose up --build --wait
```

This starts Mosquitto, PostgreSQL, all four backend services, the dashboard, and a deterministic
offline synthetic sensor simulator. No `.env` file or dataset download is required for this demo
path; the repository includes safe local defaults. The synthetic cycle is not final evaluation
evidence.

Check that every container started:

```bash
docker compose ps
```

Follow all logs:

```bash
docker compose logs -f
```

Follow only Fusion logs:

```bash
docker compose logs -f fusion-service
```

Stop the stack and keep database history:

```bash
docker compose down
```

Delete containers **and all saved PostgreSQL/MQTT data** only when you intentionally want a clean
reset:

```bash
docker compose down --volumes
```

## Linux webcam setup

Normal Compose startup does not pass a host camera into the container. On Linux, use the webcam
overlay:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.webcam.yml \
  up --build --wait
```

The defaults expect `/dev/video0` and video group ID `44`. Override them in `.env` when needed:

```dotenv
VIDEO_DEVICE=/dev/video1
VIDEO_GID=44
```

On macOS or Windows, run the Video Service directly on the host because Docker Desktop does not
provide the same Linux camera-device passthrough.

## Service addresses

| Component | Address | What it does |
|---|---|---|
| Caregiver dashboard | <http://localhost:5173> | Live state, alerts, history, trends, health, and feedback |
| Fusion API | <http://localhost:8001> | Current activity, history, trends, events, acknowledgement, WebSocket |
| Feedback API | <http://localhost:8002> | Structured feedback/summary generation and Feedback WebSocket |
| Sensor API | <http://localhost:8003> | Sensor recognition and MQTT health |
| Video API | <http://localhost:8004> | Webcam/pose recognition and health |
| Mosquitto | `localhost:1883` | MQTT message broker |
| PostgreSQL | `localhost:5432` | Persistent activity, events, and feedback tables |

Every backend has a health endpoint. For example:

```bash
curl http://localhost:8001/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

`healthy` means all managed dependencies are ready. `degraded` means the API is still alive but a
dependency, model, camera, broker, or database needs attention.

## Try the Fusion API

### Current status

```bash
curl http://localhost:8001/api/status
```

The response contains the displayed activity, confidence, last update, sensor/video online state,
and MQTT/database state.

### Activity timeline

Use UTC timestamps with `Z` or `+00:00`:

```bash
curl "http://localhost:8001/api/timeline?from=2026-07-10T00:00:00Z&to=2026-07-11T00:00:00Z&limit=100"
```

Without `from` and `to`, the API returns the most recent 24-hour range. Results are ordered from
oldest to newest.

### Safety events

```bash
curl "http://localhost:8001/api/events?from=2026-07-10T00:00:00Z&to=2026-07-11T00:00:00Z"
```

### Acknowledge an event

```bash
curl -X POST http://localhost:8001/api/events/1/ack
```

Acknowledgement is idempotent. Repeating it for the same event is safe. An unknown event ID returns
HTTP `404`.

### Activity trends

Supported periods are `1h`, `24h`, `7d`, and `30d`:

```bash
curl "http://localhost:8001/api/trends?period=24h"
```

The response includes a count and bounded observed duration for every canonical activity label.

### Live WebSocket

Connect a WebSocket client to:

```text
ws://localhost:8001/ws
```

Messages use a small typed envelope:

```json
{
  "schema_version": "1.0",
  "channel": "activity",
  "data": {
    "schema_version": "1.0",
    "ts": "2026-07-10T10:00:00Z",
    "activity": "WALKING",
    "confidence": 0.86,
    "contributors": {
      "sensor": "WALKING",
      "video": "WALKING"
    }
  }
}
```

Each browser gets a bounded queue. A very slow or dead browser is disconnected so it cannot block
safety processing for other consumers.

## Generate safe feedback and summaries

The default provider is local Ollama. Pull the configured model once, start Ollama on the host, and
then start the stack:

```bash
ollama pull llama3.2:3b
ollama serve
docker compose up --build --wait
```

Request feedback through the dashboard or directly through its same-origin route:

```bash
curl -X POST http://localhost:5173/api/feedback/generate \
  -H 'Content-Type: application/json' \
  -d '{"mode":"feedback","period":"24h","request_id":"demo-feedback-1"}'
```

Use `mode=summary` for a period recap. Supported periods are `1h`, `24h`, `7d`, and `30d`; explicit
UTC `from`/`to` values are also accepted. Reusing a `request_id` returns the persisted result instead
of generating a duplicate. Every output is schema-validated, checked for unsafe/unsupported claims,
and includes a medical-safety disclaimer. If Ollama is unavailable or its response remains invalid
after one repair attempt, the service returns deterministic fallback text when fallback is enabled.
Daily summaries run at the UTC time configured by `SUMMARY_SCHEDULE` using the daily cron form
`minute hour * * *`.

## MQTT topics

| Topic | Publisher | Consumer | Purpose |
|---|---|---|---|
| `har/sensor/raw` | Simulator | Sensor Service | Raw numeric accelerometer/gyroscope window |
| `har/sensor/prediction` | Sensor Service | Fusion Service | Sensor label, confidence, and motion intensity |
| `har/video/prediction` | Video Service | Fusion Service | Video label, confidence, and body orientation |
| `har/activity` | Fusion Service | Dashboard/Feedback | Authoritative fused activity |
| `har/event` | Fusion Service | Dashboard/Feedback | Fall, inactivity, or abnormal-pattern event |
| `har/feedback` | Feedback Service | Dashboard | Structured GenAI feedback in Milestone 4 |

Raw sensor messages use QoS 0 because they can be replayed. Predictions and final outputs use QoS 1.
Duplicate QoS-1 delivery is handled safely by in-memory message deduplication and database uniqueness
rules.

## Replay a sensor dataset

The simulator supports UCI HAR, WISDM, and SisFall. First start Mosquitto and the Sensor Service, or
start the full Compose stack. Then activate the local Python environment and run:

```bash
uv run python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --realtime \
  --speed 1 \
  --ground-truth-file data/metrics/ground-truth.jsonl
```

Ground-truth labels are written only to the optional metrics file. They are never included in the
MQTT sensor payload, so recognition cannot accidentally read the expected answer.

Use `--speed 10` for a faster replay, `--loop` to repeat, `--scenario 'PATTERN'` to select scenarios,
or `--no-realtime` to publish as fast as possible. See [the simulator guide](simulator/README.md) for
dataset layouts and more examples.

## Optional local sensor model

The model adapter targets `STMicroelectronics/IGN-HAR-model` at pinned revision
`69f07d89b9520c9ab4424fafed6d079c3d12b26d`. The application does not download a model at runtime.

To use a local model:

1. review the model's SLA0044 license;
2. place the exact `.tflite` artifact under `data/models/`;
3. set the model path and output-label order.

Example `.env` values:

```dotenv
SENSOR_MODEL_PATH=/models/your-pinned-model.tflite
SENSOR_MODEL_LABELS=STATIONARY,WALKING,EXERCISING,STAIRS
USE_FALLBACK=true
```

`SENSOR_MODEL_LABELS` must match the artifact output order exactly. Unknown model labels are safely
mapped to `UNKNOWN`. `STAIRS` maps to `WALKING`; jogging and biking map to `EXERCISING`.

If the local model is absent and `USE_FALLBACK=true`, the Sensor Service continues with deterministic
statistical rules and reports degraded model health.

## Configuration

Copy the example only when you need overrides:

```bash
cp .env.example .env
```

Important groups are listed below. Every available setting and its safe default is documented in
[.env.example](.env.example).

| Group | Important settings |
|---|---|
| Shared | `LOG_LEVEL`, `MQTT_HOST`, `MQTT_PORT`, `DATABASE_URL` |
| Sensor | `WINDOW_SIZE`, `WINDOW_OVERLAP`, `SENSOR_MODEL_PATH`, `USE_FALLBACK` |
| Video | `FPS`, `CAMERA_INDEX`, `MIN_VISIBILITY`, posture/motion thresholds |
| Fusion | `MODALITY_WEIGHTS`, `FUSION_INTERVAL`, `ALIGNMENT_TOLERANCE_MS`, `SMOOTHING_WINDOW` |
| Fall safety | `FALL_ACCEL_THRESHOLD`, `FALL_CORRELATION_MS`, cooldown/recovery settings |
| Other safety | `INACTIVITY_SECONDS`, `INACTIVITY_MOTION_THRESHOLD`, abnormal baseline settings |
| Reliability | buffer sizes, stale timeout, input/WebSocket queue sizes, API limit |
| Feedback | `LLM_MODEL`, `OLLAMA_HOST`, `GENERATION_TIMEOUT`, digest/period/fallback limits |

Do not commit passwords, API keys, or a personal `.env` file. Local ports bind to `127.0.0.1` by
default. Configure MQTT authentication and TLS before exposing the broker beyond a trusted laptop.

## Local development without Docker

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Or install the exact lock file with uv:

```bash
uv sync --frozen
```

PostgreSQL and Mosquitto must still be reachable. Start an individual API with:

```bash
uvicorn services.sensor_service.app:app --host 0.0.0.0 --port 8003
uvicorn services.video_service.app:app --host 0.0.0.0 --port 8004
uvicorn services.fusion_service.app:app --host 0.0.0.0 --port 8001
uvicorn services.feedback_service.app:app --host 0.0.0.0 --port 8002
```

Run each command in a separate terminal. The Video Service opens the configured host camera.

## Tests and quality checks

Run the complete Python suite:

```bash
pytest
```

Run formatting and lint checks:

```bash
ruff format --check .
ruff check .
```

Run the dashboard tests, type check, and production build:

```bash
cd dashboard
npm ci
npm test
npm run lint
npm run build
cd ..
```

Run the Docker smoke test:

```bash
./scripts/smoke.sh
```

The smoke test validates Compose, starts the stack, checks HTTP health, performs an MQTT round trip,
verifies that the built-in simulator reaches Fusion, and verifies PostgreSQL tables and temporary
persistence. It keeps named volumes unless
`SMOKE_REMOVE_VOLUMES=true` is set.

Validate release dependency/configuration pins and generate the repository audit:

```bash
uv run python scripts/validate_deployment.py
uv run python scripts/release_audit.py --output-dir artifacts/release
```

The audit writes JSON and Markdown evidence for dependency inventory, secret patterns, and raw-media
artifacts. Repeat it with `--runtime-path <path>` for sanitized runtime exports and optionally
`--database-url "$DATABASE_URL"` for a prepared local database. A passing automated scan covers only
the inspected paths; complete the target-laptop privacy, offline, recovery, and usability checks in
the [Milestone 5 runbook](core_docs/milestones/milestone-5-verification-release/RUNBOOK.md).

Evaluate a fixed captured scenario and write JSON, CSV, and Markdown results (including confusion
matrices):

```bash
uv run python -m tests.metrics artifacts/captures/final-scenario.json \
  --output-dir artifacts/metrics/final
```

The bundled release-demo scenario is a synthetic test fixture for the harness, not measured release
evidence. Final claims require the exact target-laptop commit, configuration, dataset/model identity,
scenario selection, and timestamp recorded in the evidence package.

Useful focused tests:

```bash
pytest tests/unit/test_fusion_core.py
pytest tests/unit/test_fusion_safety.py
pytest tests/unit/test_fusion_runtime.py
pytest tests/integration/test_fusion_api.py
pytest tests/unit/test_feedback_generation_m4.py
pytest tests/integration/test_feedback_api_m4.py
```

Do not copy test counts from an earlier run into release evidence. Record the counts, skips, commit,
UTC time, and artifacts produced by the exact candidate run.

## Common problems

### Fusion health is degraded

Check whether Mosquitto and PostgreSQL are healthy:

```bash
docker compose ps
docker compose logs mosquitto postgres fusion-service
```

### Sensor predictions do not appear

- confirm the simulator is connected to `localhost:1883`;
- confirm the Sensor Service subscribed to `har/sensor/raw`;
- check that `WINDOW_SIZE` samples have arrived;
- enable `USE_FALLBACK=true` when no local model is installed.

### Video stays degraded

- confirm the camera is not already being used by another application;
- verify `CAMERA_INDEX` and Linux `VIDEO_DEVICE`;
- use the webcam Compose overlay on Linux;
- run the Video Service on the host on macOS or Windows.

### No critical fall event appears

This can be correct. A fall requires both a sensor motion spike and horizontal video evidence within
`FALL_CORRELATION_MS`. Check Fusion logs and tune thresholds only with known test scenarios.

### Feedback uses the safe fallback

- confirm Ollama is running on the host and `OLLAMA_HOST` is reachable from the Feedback container;
- confirm the configured `LLM_MODEL` has been pulled;
- check `docker compose logs feedback-service` for provider, validation, or persistence failures;
- keep `FEEDBACK_FALLBACK_ENABLED=true` so provider failures never remove caregiver-facing guidance.

### Old history is missing

`docker compose down` keeps history. `docker compose down --volumes` deletes it. Timeline and event
queries also default to the latest 24 hours, so provide a wider UTC range when reading older records.

### A port is already in use

Change the host-facing value in `.env`, for example:

```dotenv
FUSION_SERVICE_PORT=8101
POSTGRES_PORT=55432
```

## Repository structure

```text
core_docs/             Approved functional/technical design and milestone documents
dashboard/             React caregiver UI, tests, production build, and Nginx API/WS proxy
data/                  Local datasets/models; downloaded content is ignored by Git
mosquitto/             Local broker configuration
services/
  sensor_service/      Sensor windows, features, model adapter, fallback, MQTT
  video_service/       Camera, landmarks, posture rules, MQTT
  fusion_service/      Alignment, fusion, safety, persistence, REST, WebSocket
  feedback_service/    Ollama adapter, digests, safety checks, fallback, REST/MQTT/WebSocket
shared/                Labels, schemas, topics, logging, database helpers and SQL
simulator/             UCI HAR, WISDM and SisFall loaders plus replay engine
tests/                 Unit, contract and integration tests
```

## Project documents

- [Functional specification](core_docs/FUNCTIONAL_SPEC.md)
- [Technical design](core_docs/TECHNICAL_DESIGN.md)
- [Milestone delivery map](core_docs/milestones/README.md)
- [Milestone 3 functional scope](core_docs/milestones/milestone-3-fusion-safety/FSD.md)
- [Milestone 3 technical design](core_docs/milestones/milestone-3-fusion-safety/TDD.md)
- [Milestone 3 implementation notes](core_docs/milestones/milestone-3-fusion-safety/IMPLEMENTATION.md)
- [Milestone 4 functional scope](core_docs/milestones/milestone-4-dashboard-feedback/FSD.md)
- [Milestone 4 technical design](core_docs/milestones/milestone-4-dashboard-feedback/TDD.md)
- [Milestone 4 implementation notes](core_docs/milestones/milestone-4-dashboard-feedback/IMPLEMENTATION.md)
- [Milestone 5 functional scope](core_docs/milestones/milestone-5-verification-release/FSD.md)
- [Milestone 5 technical design](core_docs/milestones/milestone-5-verification-release/TDD.md)
- [Milestone 5 implementation notes](core_docs/milestones/milestone-5-verification-release/IMPLEMENTATION.md)
- [Milestone 5 demo and operations runbook](core_docs/milestones/milestone-5-verification-release/RUNBOOK.md)
- [Milestone 5 evidence package](core_docs/milestones/milestone-5-verification-release/evidence/README.md)
- [Branching strategy](core_docs/BRANCHING_STRATEGY.md)

## Privacy and project limitations

- Raw video frames are processed in memory and discarded. They must never be stored, encoded,
  logged, or published.
- Only numeric landmarks, posture labels, confidence, orientation, and sensor numbers move between
  services.
- Logs must not contain raw sensor windows, frames, secrets, or API keys.
- Single-person local monitoring is the current scope.
- Sensor data is simulated from public datasets; no physical wearable is required.
- Model and dataset files belong under `data/` and are intentionally excluded from version control.
- Recognition quality depends on the webcam view, dataset fit, model artifact, and tuned thresholds.
- Safety events are assistive signals, not guaranteed emergency detection.
