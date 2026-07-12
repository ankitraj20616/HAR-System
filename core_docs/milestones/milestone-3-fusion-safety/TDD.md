# Milestone 3 TDD: Fusion, Safety Events, and Persistence

## 1. Architecture

The Fusion Service subscribes to `har/sensor/prediction` and `har/video/prediction`, owns the authoritative activity/event state, writes PostgreSQL, publishes MQTT, and serves REST/WebSocket endpoints.

## 2. Alignment and fusion

Maintain bounded timestamp-ordered buffers per modality. Every `FUSION_INTERVAL` (default one second), select the nearest fresh prediction inside `ALIGNMENT_TOLERANCE_MS`. Discard or count messages older than retention; handle duplicates with a message identity or timestamp/modality key.

For each label, compute `score(label) = sum(modality_weight * prediction_confidence)` for modalities predicting that label. Normalize active weights when one modality is missing. Select the highest score, with deterministic tie handling (prefer previous stable label, then `UNKNOWN`). Store source labels in `contributors`.

Apply majority or hysteresis smoothing over `SMOOTHING_WINDOW` intervals. Keep raw fused and displayed stable state separate for debugging and metrics.

## 3. Event state machines

Fall candidate begins when `motion_intensity >= FALL_ACCEL_THRESHOLD`. Confirm only if horizontal video evidence appears within `FALL_CORRELATION_MS`. Create one event, enter cooldown, and re-arm only after upright/low-motion recovery or timeout. Persist evidence, thresholds, timestamps, and contributor confidence.

Inactivity tracks continuous low-motion/rest duration and raises once at `INACTIVITY_SECONDS`; it resets on meaningful activity. Abnormal pattern is optional/Should and must use an explicit simple baseline rule, not an unexplained medical judgment.

## 4. Persistence and API

Use transaction boundaries so a stored activity/event corresponds to its publication attempt. Define retry/outbox behavior or clearly record that MQTT/WS delivery is best-effort while DB is authoritative. Queries validate time ranges, use timestamp indexes, sort consistently, and limit result size.

WebSocket envelope is `{channel, data}`. Maintain connected clients, remove dead sockets, and use bounded queues so a slow browser cannot block Fusion. Status determines online/offline from last-message age.

## 5. Reliability and observability

Metrics/logs include input count by modality, validation failures, stale/late messages, fusion latency, chosen label, event count, DB failures, and active WebSocket clients. Do not log raw frames or secrets.

On MQTT reconnect, resubscribe. On temporary DB failure, report degraded and retry safely without creating duplicate event records. Configuration includes modality weights, smoothing, alignment tolerance, fall thresholds/correlation/cooldown, inactivity, and stale timeout.

## 6. Tests

- Unit tables for weighted voting, ties, missing sources, smoothing, stale messages.
- State-machine tests for true fall, ordinary lying, spike only, horizontal only, duplicate evidence, recovery/re-arm.
- Persistence tests for timeline, events, range queries, trends, and idempotent acknowledgement.
- API schema and error tests.
- Integration replay through MQTT to DB and WebSocket.
- Latency measurement from source timestamp to emitted activity/event.

## 7. Branch plan and release

- `feat/fusion-time-alignment`
- `feat/fusion-weighted-voting`
- `feat/fusion-temporal-smoothing`
- `feat/fusion-fall-detection`
- `feat/fusion-history-api`
- `test/fusion-resilience-cases`

Shared schema changes need two approvals. Tag completion `v0.3-m3`.

