# Milestone 1 FSD: Foundation and Shared Contracts

## 1. Goal

Create a stable base on which all services can be developed independently. At the end, the team can start MQTT and PostgreSQL, run service skeletons, validate shared messages, and see clear health and logs.

## 2. Users and value

- Developers get one predictable repository structure and one-command startup.
- Reviewers can clone the project and confirm that the base system works.
- Later services share the same labels, topics, schemas, timestamps, and configuration rules.

## 3. In scope

- Repository folders for four backend services, dashboard, simulator, shared code, tests, and data.
- Mosquitto and PostgreSQL in Docker Compose.
- Shared activity/event constants and message validation.
- Database initialization for timeline, events, and feedback.
- Environment-based configuration and `.env.example`.
- Health endpoints, structured logs, basic automated tests, and pull-request CI.

## 4. Out of scope

No real activity recognition, webcam inference, fusion, fall alert, LLM response, or finished dashboard is required in this milestone.

## 5. Functional requirements

| ID | Priority | Behaviour | Acceptance |
|---|---|---|---|
| M1-F1 | Must | A documented command starts Mosquitto, PostgreSQL, and service skeletons. | Fresh checkout reaches healthy state without manual container setup. |
| M1-F2 | Must | All components use one canonical label and event list. | Invalid labels are rejected by shared validation. |
| M1-F3 | Must | Shared MQTT payload schemas validate timestamps, confidence, and required fields. | Valid examples pass and malformed examples fail in contract tests. |
| M1-F4 | Must | PostgreSQL stores activity, event, and feedback records. | Migration/init creates all tables and indexes; a smoke test inserts and reads rows. |
| M1-F5 | Must | Configuration is supplied without source-code edits. | Broker, database, ports, and log settings change through environment values. |
| M1-F6 | Must | Every backend service exposes a health check and useful logs. | Health response identifies service and status; logs include time, level, service, and message. |
| M1-F7 | Should | CI checks formatting, lint, tests, and image builds. | A broken test blocks pull-request merge. |

This milestone prepares FR-X1, FR-X3, FR-X4 and NFR-6, NFR-9, NFR-10.

## 6. Main flows

### Startup flow

1. Developer copies `.env.example` if needed.
2. Developer runs the documented Compose command.
3. PostgreSQL initializes its schema and Mosquitto accepts local clients.
4. Service skeletons connect or report a clear degraded state.
5. Health checks and logs confirm readiness.

### Contract change flow

1. Developer proposes the schema change on a `feat/shared-*` branch.
2. Contract examples and tests are updated.
3. Two team members review the pull request.
4. Dependent services rebase after merge.

## 7. Data rules

- Timestamps use ISO-8601 UTC and are timezone-aware in PostgreSQL.
- Confidence is a number from 0 to 1.
- Unknown input maps to `UNKNOWN`; services must not invent labels.
- Event severity is `info`, `warning`, or `critical`.
- Secrets are never committed. Dataset files and model weights remain gitignored.

## 8. Non-functional expectations

- Startup failures explain the missing dependency or invalid setting.
- Containers restart safely without deleting persistent database history.
- Components are pinned to reproducible versions.
- The base remains small enough for a standard 8 GB laptop.

## 9. Exit checklist

- [ ] Fresh checkout starts successfully with the documented command.
- [ ] Broker publish/subscribe smoke test passes.
- [ ] Database create/insert/read smoke test passes.
- [ ] All shared contract tests pass.
- [ ] Each service health endpoint responds.
- [ ] CI runs on pull requests.
- [ ] No secrets, datasets, raw video, or model binaries are tracked.

## 10. Dependencies and hand-off

There is no earlier milestone. Milestone 2 may begin only after topic names, canonical labels, message version policy, and configuration conventions are accepted.

