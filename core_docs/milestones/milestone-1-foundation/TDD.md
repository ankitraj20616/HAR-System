# Milestone 1 TDD: Foundation and Shared Contracts

## 1. Technical outcome

Build the common runtime and contracts while keeping business logic as small stubs. Python 3.11+, FastAPI, Pydantic, paho-mqtt, PostgreSQL, pytest, Docker Compose, and GitHub Actions are the baseline.

## 2. Target structure

```text
services/{sensor_service,video_service,fusion_service,feedback_service}/
shared/{schemas.py,topics.py,labels.py,db.py,config.py}
simulator/
dashboard/
tests/{unit,contract,integration}/
data/                         # gitignored
docker-compose.yml
.env.example
```

## 3. Shared contracts

Define typed schemas for `SensorRaw`, `SensorPrediction`, `VideoPrediction`, `FusedActivity`, `HAREvent`, and `Feedback`. Validate confidence bounds, UTC timestamps, enum values, non-empty sensor windows, and allowed severity. Add a contract version field or document backward-compatible evolution before Milestone 2.

Topics are constants: `har/sensor/raw`, `har/sensor/prediction`, `har/video/prediction`, `har/activity`, `har/event`, and `har/feedback`. MQTT clients use stable client IDs, reconnect backoff, QoS 1 for events and predictions, and do not silently discard validation errors.

## 4. Database design

Create `activity_timeline`, `events`, and `feedback` using the DDL in the main TDD. Add timestamp indexes and database readiness checks. Use a migration or repeatable initialization script; initialization must be safe to run twice. Keep persistence behind shared helper/repository functions so tests can substitute a test database.

## 5. Service skeleton design

Each FastAPI service provides `GET /health` returning service name, status, version, and dependency states. Startup creates required MQTT/DB connections; shutdown closes them cleanly. A dependency failure gives `degraded` rather than an unhandled crash when useful work can continue.

Structured log fields: `ts`, `level`, `service`, `event`, `message`, and optional `correlation_id`. Never log API keys, full raw sensor windows by default, or frame data.

## 6. Compose design

Compose includes PostgreSQL, Mosquitto, four backend skeletons, and a dashboard placeholder. Use named volumes for database data, health checks, dependency conditions where supported, and explicit ports. Configuration comes from environment variables with safe development defaults.

Core variables: `MQTT_HOST`, `MQTT_PORT`, `DATABASE_URL`, service ports, `LOG_LEVEL`, and `MESSAGE_SCHEMA_VERSION`. `.env.example` contains placeholders, not secrets.

## 7. Tests

- Unit: enums, settings parsing, schema validation, timestamp conversion.
- Contract: every example from the main TDD passes; missing/invalid fields fail.
- Integration: publish a test MQTT message, initialize DB, insert/read one record, call all health endpoints.
- Compose smoke: services become healthy from a clean environment.

## 8. Branch and PR plan

- `chore/infra-repo-skeleton`
- `chore/infra-docker-compose`
- `feat/shared-contracts` (two approvals)
- `feat/shared-database-schema` (two approvals)
- `chore/infra-ci`

Use squash merge. Tag the accepted result `v0.1-m1`.

## 9. Definition of done

Code, tests, `.env.example`, startup instructions, schema examples, and health checks are reviewed. CI is green and a new clone can reach a healthy base without undocumented steps.

