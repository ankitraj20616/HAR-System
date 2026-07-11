# Milestone 5 demo and operations runbook

This runbook is the operator procedure for the final single-laptop demonstration. Run commands from
the repository root unless a step says otherwise. Record results in [`evidence/`](evidence/README.md)
using `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`; never infer a pass from expected behavior.

## 1. Online preparation

Use the intended target laptop. Minimum prerequisites are Git, Docker Engine with Compose v2,
`curl`, `uv` (the release/CI pin is recorded in the dependency inventory), at least 8 GB RAM, and
sufficient free disk for images, PostgreSQL, datasets, and the local model. Python 3.11 or 3.12 is
needed for local replay/evaluation. A webcam is needed for live fusion.

1. Check out the exact candidate and confirm it has no local changes:

   ```bash
   git switch feature/milestone-5
   git pull --ff-only
   git status --short
   git rev-parse HEAD
   ```

   Save the commit. `git status --short` must be empty before tagging.

2. Copy `.env.example` only when overrides are needed. Review the values, remove cloud keys, and
   keep `.env` untracked:

   ```bash
   cp .env.example .env
   git check-ignore .env
   ```

3. Place the approved extracted dataset under `data/`. Place any pinned `.tflite` file under
   `data/models/`, configure `/models/<filename>.tflite`, its exact label order, model ID, and
   revision, and record its SHA-256. These files are intentionally not committed.

4. If local Ollama output is part of the demo, prepare it while online:

   ```bash
   ollama pull llama3.2:3b
   ollama list
   ```

   Keep `FEEDBACK_FALLBACK_ENABLED=true`. The deterministic fallback is the supported degraded path
   if Ollama is unavailable; it must still be tested for safe, disclaimed output.

5. Materialize dependencies and container images while online:

   ```bash
   uv sync --frozen
   (cd dashboard && npm ci)
   docker compose build
   docker compose up --detach --wait
   docker compose down
   ```

6. Run all automated gates and save terminal logs without secrets or raw payloads:

   ```bash
   uv run ruff format --check .
   uv run ruff check .
   uv run pytest
   (cd dashboard && npm test && npm run lint && npm run build)
   docker compose config --quiet
   uv run python scripts/validate_deployment.py
   uv run python scripts/release_audit.py --output-dir artifacts/release
   SMOKE_REMOVE_VOLUMES=true ./scripts/smoke.sh
   ```

7. Complete the dependency/license inventory and release audit documented in
   [`evidence/dependency-inventory.md`](evidence/dependency-inventory.md). Resolve exposed-secret,
   prohibited artifact, or unresolved-license findings before proceeding.

## 2. Clean start

The following reset permanently deletes the project's named PostgreSQL and MQTT volumes. Export only
approved report evidence first; never back up raw video.

```bash
docker compose down --volumes --remove-orphans
docker compose up --build --wait
```

The second line is the one-command demo start for broker, database, four services, dashboard, and the
built-in offline synthetic sensor simulator. The simulator cycles deterministic quiet-upright,
walking-like, and vigorous-motion input; it is for demonstration, not evaluation evidence. Its
configurable settings are `SIMULATOR_DEVICE_ID`, `SIMULATOR_SAMPLING_HZ`,
`SIMULATOR_CHUNK_SECONDS`, and `SIMULATOR_SCENARIO_SECONDS`. On Linux, replace the start command with
the webcam overlay when camera passthrough is required:

```bash
docker compose -f docker-compose.yml -f docker-compose.webcam.yml up --build --wait
```

On macOS or Windows, keep the remaining stack in Compose and run the Video Service in the prepared
Python environment with `MQTT_HOST=localhost` and the configured `CAMERA_INDEX`:

```bash
uvicorn services.video_service.app:app --host 127.0.0.1 --port 8004
```

Stop the Compose `video-service` first to avoid a port collision. This is a documented fallback,
not the one-command Linux path.

## 3. Expected health

Inspect container and API state before demonstrating recognition:

```bash
docker compose ps
for port in 8001 8002 8003 8004; do curl --fail --silent "http://localhost:${port}/health"; echo; done
curl --fail --silent http://localhost:5173/health; echo
curl --fail --silent http://localhost:8001/api/status; echo
```

PostgreSQL, Mosquitto, Fusion, Feedback, Sensor, and dashboard should be running. Fusion must report
healthy MQTT/database dependencies. Sensor may explicitly report degraded when the approved local
model is absent and deterministic fallback is enabled. Video may report degraded until a camera is
available. For the full fusion demo, `/api/status` must show both modalities online after replay and
camera predictions begin; do not record that check as passed merely because the HTTP API responds.

## 4. Demo scenario order

Open <http://localhost:5173> and keep the alert area visible. Record UTC start/end time, scenario
IDs, operator actions, observed UI/API behavior, and screenshot filenames. Screenshots must not show
raw camera imagery, personal information, credentials, or unredacted local paths.

1. **Cold state:** confirm clear loading/stale/offline states before predictions arrive.
2. **Normal activity:** replay fixed walking, sitting, standing, lying, and exercising scenarios.
   Confirm live activity, history, and trends update.
3. **Unknown/no-person:** leave the camera without a person or use the fixed unknown scenario.
   Confirm an explicit unknown/stale state rather than a fabricated confident activity.
4. **False-alarm controls:** demonstrate ordinary lying, vigorous upright motion, and horizontal
   posture without a sensor spike. Confirm no critical fall is created.
5. **True fall:** use the agreed acted or SisFall scenario while safely presenting horizontal video
   evidence within `FALL_CORRELATION_MS`. Do not physically fall. Confirm exactly one prompt critical
   event, acknowledge it once, and confirm repeated acknowledgement is harmless.
6. **Feedback:** request feedback and a period summary. Confirm relevance to stored facts, structured
   rendering, fallback behavior where applicable, and the non-medical disclaimer.
7. **Degraded modes:** stop one modality at a time and confirm the other continues without a process
   crash. Record status and recovery times.
8. **Persistence:** note recent timeline/event/feedback IDs, restart the stack without `--volumes`,
   and confirm those records and acknowledgements remain.

For final metrics, use a fixed labeled dataset replay instead of treating the built-in synthetic
demo cycle as ground truth. Use a fixed, recorded scenario pattern rather than an arbitrary subset:

```bash
uv run python -m simulator.replay \
  --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" \
  --scenario 'REPLACE_WITH_FIXED_PATTERN' \
  --speed 1 \
  --ground-truth-file data/metrics/ground-truth.jsonl
```

For a SisFall fall-control replay:

```bash
uv run python -m simulator.replay \
  --dataset sisfall \
  --dataset-path data/SisFall_dataset \
  --scenario 'REPLACE_WITH_FIXED_FALL_SCENARIO' \
  --speed 1 \
  --ground-truth-file data/metrics/sisfall-ground-truth.jsonl
```

Ground-truth files are evaluation inputs/artifacts and remain outside inference messages. Replace
placeholders before rehearsal; do not claim the generic examples are the frozen final set.

After converting the independently captured ground truth/predictions/events/timestamps to the
metrics input contract, generate the report with:

```bash
uv run python -m tests.metrics artifacts/captures/final-scenario.json \
  --output-dir artifacts/metrics/final
```

The bundled `tests/metrics/scenarios/release_demo_v1.json` is an illustrative synthetic fixture for
testing the harness. Its favorable values are not measured release results and must not appear in
the final report as evidence.

## 5. Failure injection and recovery

Run one fault at a time. Capture `docker compose ps`, affected `/health` responses, relevant logs,
whether unaffected paths continued, and time to recovery.

| Fault | Inject | Expected safe behavior | Recover |
|---|---|---|---|
| Camera/video loss | `docker compose stop video-service` | Sensor path and dashboard stay alive; video becomes offline/stale; no crash | `docker compose start video-service` |
| Sensor loss | `docker compose stop simulator` (or stop a local replay with `Ctrl+C`) | Video path stays alive; sensor becomes offline/stale; no fabricated sensor result | `docker compose start simulator` or restart the exact replay command |
| Broker restart | `docker compose restart mosquitto` | Services expose degraded/reconnecting state; no process-wide failure | Wait for reconnect; verify health and new messages |
| Database restart | `docker compose restart postgres` | API exposes degraded persistence; no false success for failed writes | Wait for healthy DB; verify a new record persists |
| Ollama unavailable | Stop local Ollama, then request feedback | Bounded timeout and deterministic safe fallback; alerts remain independent | Start Ollama; verify `ollama list`; retry with a new request ID |
| Browser reconnect | Close/reopen or disable/re-enable browser network | WebSocket reconnects and REST refresh fills current/history state | Reload only if automatic reconnect does not recover |

Never use a real emergency, unsafe acted fall, malformed production database, or untrusted network
to inject a failure.

## 6. Logs and diagnosis

Container logs are the canonical runtime log source:

```bash
docker compose logs --since 15m --timestamps
docker compose logs --since 15m --timestamps fusion-service
docker compose logs --since 15m --timestamps sensor-service video-service feedback-service
```

Save only the minimum excerpt needed for evidence. Before including it, scan for secrets, connection
URLs, raw sensor arrays, landmarks, image/frame material, and personal information. Expected useful
events include service lifecycle, dependency state, accepted predictions, fused results, persistence
failures, safety events, and feedback validation/fallback. A stack trace alone is not evidence that
recovery succeeded; pair it with health and post-recovery behavior.

## 7. Persistence restart and reset

Restart while retaining history:

```bash
docker compose down
docker compose up --wait
```

Confirm recorded timeline/events through the dashboard or API. For an intentional destructive reset:

```bash
docker compose down --volumes --remove-orphans
```

After a destructive reset, repeat clean start and health checks. Never use `--volumes` during the
persistence-retention test.

## 8. Offline rehearsal

Prepare every dependency, image, dataset, and model online first. Record the network-disabling method
appropriate to the target laptop; do not disable networking on a remotely administered machine.

1. Stop the stack, disable Wi-Fi/Ethernet, and verify public internet access fails.
2. Start with already-built local images:

   ```bash
   docker compose up --no-build --wait
   ```

3. Run health, normal, false-alarm, true-fall, feedback/fallback, persistence, and recovery checks.
4. Monitor logs for attempted downloads, DNS calls, cloud-provider calls, or missing artifacts.
5. Stop the stack, restore networking, and complete
   [`evidence/offline-checklist.md`](evidence/offline-checklist.md).

An API response from a running stack is not sufficient: the complete agreed scenario must run while
external networking is demonstrably unavailable.

## 9. Privacy and usability observations

Complete [`evidence/privacy-checklist.md`](evidence/privacy-checklist.md) after scanning database
tables, named volumes, logs, MQTT payload schemas, generated artifacts, screenshots, and feedback
digests. Any persisted/transmitted raw frame is a Must failure.

For usability, give the test participant only the caregiver role and safety disclaimer. Do not point
to the answer. Ask them to identify current state, sensor/video health, a critical fall, how to
acknowledge it, and where to find history. Record observations and consent-safe notes in
[`evidence/usability-notes.md`](evidence/usability-notes.md), never names or medical details.

## 10. Shutdown and release sequence

Stop containers while retaining the rehearsal database:

```bash
docker compose down
```

Then follow this exact gate:

1. freeze dependencies/config and run automated plus release-only verification;
2. review traceability and confirm every Must is `PASS` with an artifact;
3. rehearse from a clean checkout on the target laptop, then rehearse offline;
4. confirm `git status --short` is empty and record `git rev-parse HEAD`;
5. create annotated tag `v1.0-demo` only for that tested commit;
6. update report/PPT references without changing tested behavior;
7. rerun the smoke test and affected documentation/audit checks;
8. create annotated tag `v1.0-submission` for the exact submitted state.

Suggested local tag commands after every gate is signed off:

```bash
git tag -a v1.0-demo -m "HAR System v1.0 demo"
git show --no-patch --decorate v1.0-demo
```

Do not push tags unless the release owner explicitly authorizes it. Never tag with a failing Must,
uncommitted configuration, missing license decision, exposed secret, or unresolved evidence link.
