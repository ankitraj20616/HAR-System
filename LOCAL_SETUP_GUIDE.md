# HAR System local setup and prototype guide

This guide takes a new developer from a clean checkout to the complete local prototype. Commands
are run from the repository root. The fastest path is:

```bash
./dev.sh up
```

The command checks Docker and `.env`, builds the images, waits for service health, and seeds an empty
PostgreSQL database. Supabase must be configured first; follow
[`SUPABASE_SETUP.md`](core_docs/milestones/milestone-6-auth-rbac/SUPABASE_SETUP.md). Open
<http://localhost:5173> to show the prototype.

## 1. Prerequisites

- Docker Engine or Docker Desktop with Compose v2 (`docker compose version`)
- Git
- 8 GB RAM recommended
- `curl` for `./dev.sh status` and smoke checks
- Linux webcam only for live camera input; it is not required for the seeded prototype
- Python 3.11/3.12 only for host-side development and tests
- Optional: Ollama for locally generated AI feedback
- A Supabase project and network access for signup/login/session refresh

Docker must be running and the current user must be allowed to use it. Verify the checkout once:

```bash
./dev.sh setup
```

## 2. Start, inspect, and stop the stack

```bash
./dev.sh up
./dev.sh status
./dev.sh logs
./dev.sh logs fusion-service
./dev.sh restart feedback-service
./dev.sh down
```

`down` preserves PostgreSQL and MQTT volumes. A later `up` keeps existing data. To replace database
content with a clean, current-time prototype dataset:

```bash
./dev.sh seed
```

Warning: `seed` intentionally clears the three application tables before adding demo activities,
events, and feedback. It does not delete Docker volumes or configuration.

To run the automated integration path:

```bash
./dev.sh smoke
```

The smoke script starts the stack, checks HTTP, MQTT, PostgreSQL, persistence, simulator flow, and
dashboard proxying, then stops it. Set `SMOKE_KEEP_RUNNING=true` to leave it running.

## 3. Services and addresses

| Compose service | Host address | Responsibility |
|---|---|---|
| `dashboard` | <http://localhost:5173> | Caregiver UI, alerts, timeline, trends, feedback |
| `auth-service` | <http://localhost:8005> / [API docs](http://localhost:8005/docs) | Public JWT/RBAC gateway |
| `fusion-service` | Docker-internal `fusion-service:8001` | Authoritative fused activity and events |
| `feedback-service` | Docker-internal `feedback-service:8002` | Safe feedback and summaries |
| `sensor-service` | <http://localhost:8003> / [API docs](http://localhost:8003/docs) | Sensor windows and activity prediction |
| `video-service` | <http://localhost:8004> / [API docs](http://localhost:8004/docs) | Pose-only video activity prediction |
| `mosquitto` | `localhost:1883` | MQTT broker between services |
| `postgres` | `localhost:5432` | Timeline, events, and feedback persistence |
| `simulator` | no HTTP port | Continuous deterministic wearable-data demo |

The dashboard proxies `/api/*` and WebSockets to Auth Service. Fusion/Feedback are not host-published.
The browser receives only the Supabase publishable key; backend secrets never enter the React build.

## 4. Environment configuration

`.env.example` is the complete, documented template. `./dev.sh setup` copies it to `.env` only when
`.env` does not already exist. Never commit `.env` or real credentials.

Replace the Supabase/ticket placeholders before `./dev.sh up`. Important groups are:

| Variables | Where the value comes from |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Choose local-only values; template defaults work immediately |
| `*_SERVICE_PORT`, `DASHBOARD_PORT`, `MQTT_PORT`, `POSTGRES_PORT` | Any unused localhost ports; keep defaults unless there is a conflict |
| `WINDOW_*`, fusion/safety thresholds, video thresholds | Project-tested defaults in `.env.example`; change only while tuning |
| `SENSOR_MODEL_PATH`, `SENSOR_MODEL_LABELS` | Optional licensed `.tflite` artifact and its exact class order; place artifact in `data/models/` |
| `VIDEO_DEVICE`, `VIDEO_GID` | Linux device path from `ls /dev/video*` and group ID from `getent group video` |
| `OLLAMA_HOST`, `LLM_MODEL` | Local Ollama installation and a model shown by `ollama list` |
| `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Not used by the current Ollama adapter; leave blank |
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | Your Supabase project; publishable key is browser-safe |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional server-only key required for admin role changes |
| `AUTH_TICKET_SECRET` | Random 32+ character backend-only WebSocket signing secret |

Do not search for or invent cloud API keys. If a future adapter requires one, obtain it only from
your own account in that provider's official developer console, restrict its permissions/budget,
store it only in `.env`, and never expose it through `VITE_*` variables.

Compose constructs its internal `DATABASE_URL` and uses Docker DNS names (`postgres`, `mosquitto`).
The `DATABASE_URL=...localhost...` value in `.env` is for services run directly on the host.

### Optional Ollama feedback

The system remains demo-ready without Ollama because safe deterministic fallback feedback is
enabled. For local model output, install Ollama from its official distribution, then run:

```bash
ollama pull llama3.2:3b
ollama serve
ollama list
```

Keep these defaults for a host Ollama reached from Compose:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_HOST=http://host.docker.internal:11434
FEEDBACK_FALLBACK_ENABLED=true
```

### Optional sensor model

The fallback sensor classifier is enabled by default and needs no download. To provision a model:

1. Obtain the exact artifact from its model publisher and accept its license.
2. Put it at `data/models/model.tflite`.
3. Set the container path and exact output-label order:

```dotenv
SENSOR_MODEL_PATH=/models/model.tflite
SENSOR_MODEL_LABELS=STANDING,WALKING,SITTING,LYING,EXERCISING,UNKNOWN
USE_FALLBACK=false
```

Never guess label order; it must match that exact artifact.

### Optional Linux webcam

```bash
ls -l /dev/video*
getent group video
HAR_WEBCAM=true VIDEO_DEVICE=/dev/video0 ./dev.sh up
```

Put persistent overrides in `.env`. On macOS/Windows, Docker Desktop does not provide equivalent
Linux device passthrough; run the video service on the host for live capture. Without a camera it
stays safely degraded and the seeded/sensor prototype still works.

## 5. Prototype walkthrough

1. Run `./dev.sh seed` immediately before presenting for stable, fresh demo content.
2. Open the dashboard and point out live system status from the simulator.
3. Show the six-hour timeline and activity distribution in Trends.
4. Open Alerts: seeded abnormal-pattern and inactivity events are acknowledged; the fall remains
   unacknowledged so the critical banner is visible.
5. Acknowledge the sample fall to demonstrate the write path.
6. Show the seeded feedback summary. Optionally generate fresh feedback to demonstrate Ollama or
   the safe fallback path.
7. Run `./dev.sh status` and, if needed, `./dev.sh logs service-name` for operational visibility.

This is an assistive college prototype, not a medical device or emergency-response replacement.

## 6. Host-side development and tests

Docker is sufficient for the prototype. For Python development:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest
```

For dashboard development:

```bash
cd dashboard
npm ci
npm run dev
```

Use `dashboard/.env.example` for optional direct backend URLs. Blank values use the development
proxy and are preferred.

## 7. Troubleshooting

- `Docker is not reachable`: start Docker Engine/Desktop; on Linux check Docker group access.
- Port already allocated: change the matching host-facing port in `.env`, then rerun `up`.
- Service unhealthy: run `./dev.sh status`, then `./dev.sh logs <service>`.
- Camera degraded: expected without webcam passthrough; use `HAR_WEBCAM=true` only on Linux.
- Feedback provider unavailable: check `ollama list` and `OLLAMA_HOST`; deterministic fallback stays available.
- Need a fresh prototype: run `./dev.sh seed` (application data only).
- Need to delete all persisted state: run `docker compose down --volumes` only when that data loss is intentional.

For deeper release/evidence procedures, see
`core_docs/milestones/milestone-5-verification-release/RUNBOOK.md`.
