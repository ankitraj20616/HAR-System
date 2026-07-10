# HAR System

A software-only, privacy-first Human Activity Recognition foundation for patient monitoring. Milestone
1 provides shared message contracts, PostgreSQL persistence, an MQTT broker, four FastAPI service
skeletons, and a dashboard placeholder. Real activity recognition, fusion, GenAI, and the finished
dashboard are delivered in later milestones.

## Start everything with one command

Prerequisites: Docker Engine with Docker Compose v2 and at least 8 GB RAM.

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

## Services and ports

| Component | Local address | Purpose |
|---|---|---|
| Dashboard | <http://localhost:5173> | Milestone 1 readiness page |
| Fusion service | <http://localhost:8001/health> | Fusion API skeleton and database/MQTT health |
| Feedback service | <http://localhost:8002/health> | Feedback API skeleton and database/MQTT health |
| Sensor service | <http://localhost:8003/health> | Sensor API skeleton and MQTT health |
| Video service | <http://localhost:8004/health> | Video API skeleton and MQTT health |
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

For local Python development:

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

## Configuration

All configuration is environment-driven. [.env.example](.env.example) documents safe development
defaults for service ports, logging, schema version, sensor windows, video settings, fusion thresholds,
and feedback-provider selection. Secrets must be supplied only through an untracked `.env` or another
secret manager. The default feedback provider is a deterministic offline template and needs no API key.

## Repository map

```text
services/       Four FastAPI backend services
shared/         Canonical labels, topics, schemas, configuration, logging, and database helpers
simulator/      Software sensor-stream placeholder
dashboard/      Milestone 1 health-capable dashboard placeholder
mosquitto/      Local broker configuration
tests/          Unit, contract, and integration tests
core_docs/      Functional and technical specifications plus milestone plans
```

See [Milestone 1 FSD](core_docs/milestones/milestone-1-foundation/FSD.md) and
[Milestone 1 TDD](core_docs/milestones/milestone-1-foundation/TDD.md) for scope and acceptance criteria.

## Privacy and safety

- Raw camera frames must never be stored or published.
- Logs must not contain full sensor windows, frames, secrets, or API keys.
- This academic prototype is an assistive tool, not a medical device or diagnosis system.
- Dataset files and model weights belong under `data/`, which is intentionally ignored by Git.
