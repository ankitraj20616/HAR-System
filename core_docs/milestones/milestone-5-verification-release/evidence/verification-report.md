# Final verification report template

**Overall status:** `NOT RUN`

## Run identity

| Field | Recorded value |
|---|---|
| Candidate commit | `PENDING` |
| Worktree clean | `PENDING` |
| UTC start/end | `PENDING` |
| Operator / reviewer role | `PENDING` |
| Hardware (CPU/RAM/GPU/camera) | `PENDING` |
| OS, kernel, Docker/Compose | `PENDING` |
| Python / Node / browser | `PENDING` |
| Dataset name/version/hash | `PENDING` |
| Fixed scenario selection | `PENDING` |
| Label mapping version/path | `PENDING` |
| Sensor model ID/revision/hash | `PENDING` |
| Video model/package identity | `PENDING` |
| LLM provider/model identity | `PENDING` |
| Redacted config path/hash | `PENDING` |
| Random seed, if applicable | `PENDING` |
| Metrics output directory/hash | `PENDING` |

Do not paste secrets into the recorded config. Hash the exact redacted/frozen configuration used.

## Automated gates

| Gate | Command | Status | UTC / artifact |
|---|---|---|---|
| Python format | `uv run ruff format --check .` | `NOT RUN` | `PENDING` |
| Python lint | `uv run ruff check .` | `NOT RUN` | `PENDING` |
| Python tests | `uv run pytest` | `NOT RUN` | `PENDING` |
| Dashboard tests | `(cd dashboard && npm test)` | `NOT RUN` | `PENDING` |
| Dashboard type/lint | `(cd dashboard && npm run lint)` | `NOT RUN` | `PENDING` |
| Dashboard build | `(cd dashboard && npm run build)` | `NOT RUN` | `PENDING` |
| Compose validation | `docker compose config --quiet` | `NOT RUN` | `PENDING` |
| Dependency/deployment pins | `uv run python scripts/validate_deployment.py` | `NOT RUN` | `PENDING` |
| Stack smoke | `SMOKE_REMOVE_VOLUMES=true ./scripts/smoke.sh` | `NOT RUN` | `PENDING` |
| Release/privacy/secret audit | `uv run python scripts/release_audit.py --output-dir artifacts/release` plus target runtime/DB paths | `NOT RUN` | `PENDING` |

Record test counts and skips from output; never carry forward a count from an earlier milestone.

## Recognition comparison

State the averaging/alignment policy and sample/event count. Link the complete per-class
precision/recall/F1 table and confusion matrix rather than copying only favorable classes.

| Mode | Macro F1 | Weighted F1 | Artifact | Status |
|---|---:|---:|---|---|
| Sensor-only | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |
| Video-only | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |
| Raw fusion | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |
| Smoothed fusion | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |

**Fusion exceeds both single modalities on the agreed metric:** `NOT RUN`

## Fall-event results

Record event matching tolerance and enforce one-to-one matching so duplicate alerts cannot become
multiple true positives.

| True events | Predicted events | TP | FP | FN | Precision | Recall | F1 | Duplicate alerts | Status |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |

False-alarm controls run: `PENDING`. Artifact: `PENDING`.

## End-to-end latency

Latency begins at the declared source/event timestamp and ends when the corresponding update is
dashboard-receivable over WebSocket. Record clock method and any excluded samples.

| Path | Count | Median ms | p95 ms | Max ms | Target | Status | Artifact |
|---|---:|---:|---:|---:|---|---|---|
| Activity update | `PENDING` | `PENDING` | `PENDING` | `PENDING` | target `< 1 s` | `NOT RUN` | `PENDING` |
| Fall alert | `PENDING` | `PENDING` | `PENDING` | `PENDING` | target about `1–2 s` | `NOT RUN` | `PENDING` |

## Reliability, load, and recovery

| Scenario | Continued service | Recovery time | Queue/memory observation | Status | Artifact |
|---|---|---:|---|---|---|
| Camera loss/recovery | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| Sensor replay stop/recovery | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| MQTT restart | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| PostgreSQL restart | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| LLM timeout/invalid output | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| Browser reconnect | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| Expected-rate soak/load | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |

## Linked release-only evidence

| Area | Record | Status |
|---|---|---|
| Privacy | [privacy-checklist.md](privacy-checklist.md) | `NOT RUN` |
| Offline | [offline-checklist.md](offline-checklist.md) | `NOT RUN` |
| Usability | [usability-notes.md](usability-notes.md) | `NOT RUN` |
| Cost/license | [dependency-inventory.md](dependency-inventory.md) | `NOT RUN` |
| Traceability | [requirement-traceability.md](requirement-traceability.md) | `NOT RUN` |

## Decision

**Decision:** `NOT RUN`  
**Must blockers:** `PENDING`  
**Deviations/exclusions:** `PENDING`  
**Reviewer sign-off and UTC time:** `PENDING`

This result is for an academic assistive prototype, not a medical device or clinical-accuracy claim.
