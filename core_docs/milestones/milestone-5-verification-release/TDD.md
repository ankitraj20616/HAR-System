# Milestone 5 TDD: Verification, Hardening, and Final Release

## 1. Metrics harness

Place evaluation tooling under `tests/metrics/`. A run consumes fixed labeled scenarios and captures sensor, video, raw fused, smoothed fused, events, ground truth, and processing timestamps. Keep ground truth outside inference inputs.

Compute class precision/recall/F1 using one documented averaging policy plus per-class results. Match fall events to ground truth inside a declared tolerance so one fall cannot count several times. Latency is source/event timestamp to dashboard-receivable WebSocket timestamp; record median, p95, and maximum.

Write machine-readable JSON/CSV and a human-readable Markdown summary. Include git commit, config hash, dataset version, model ID/revision, run seed where relevant, system hardware, and start/end time.

## 2. Test matrix

- Unit and contract suites from all earlier milestones.
- Full MQTT → inference → fusion → DB → WebSocket → dashboard integration.
- Failure injection for camera loss, simulator stop, MQTT reconnect, DB restart, LLM timeout/invalid output, and browser reconnect.
- Load/soak test at expected message rates with bounded queues and memory.
- Privacy scan of DB, volumes, logs, messages, and generated artifacts.
- Dependency/license inventory and secret scan.
- Offline test with network disabled after documented one-time preparation.

## 3. Tuning policy

Tune configurable window sizes, modality weights, smoothing, alignment tolerance, posture/fall thresholds, and cooldown on development/validation scenarios. Freeze them before final evaluation. Never train or fine-tune a model, and never tune against the final results until they look favorable. Store the final configuration with the release.

## 4. Deployment hardening

Pin container bases and dependencies, add health checks and restart policies, persist PostgreSQL via named volume, validate startup settings, and document resource needs. Compose should start in dependency order but services must still retry connections.

Because webcam passthrough varies by operating system, document a supported non-Docker command for Video Service while the remaining stack stays in Compose. Document local Ollama preparation and model verification. Avoid a runtime dataset/model download during the offline demo.

## 5. Demo and operations runbooks

Create a preparation checklist, clean-start command, expected health state, scenario order, reset procedure, log locations, common-failure table, and recovery steps. Rehearse once from a clean checkout and once with networking disabled. Back up only required report artifacts, never raw video.

## 6. CI and release gates

Pull requests require lint/format, unit/contract tests, integration tests feasible in CI, and image build. Heavy webcam/LLM/evaluation tests run as documented release jobs. No release is tagged with failing Must requirements, uncommitted configuration, missing license information, or exposed secrets.

Suggested final branches: `test/metrics-comparison`, `test/end-to-end-demo`, `fix/*` for discovered defects, `docs/demo-runbook`, and `docs/final-report-evidence`. Use squash merge and delete branches.

## 7. Evidence package

Keep final configuration, metrics summary, confusion matrix, fall results, latency results, privacy checklist, offline checklist, usability notes, dependency inventory, known limitations, and screenshots that contain no sensitive/raw-camera content. Link each result back to its `FR-*`/`NFR-*` requirement.

## 8. Release sequence

1. Freeze dependencies/config and run all gates.
2. Rehearse the exact demo on the target laptop.
3. Tag `v1.0-demo` and record its commit.
4. Complete report/PPT references without changing tested behaviour.
5. Run a final smoke test and tag `v1.0-submission`.

