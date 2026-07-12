# Milestone 3 FSD: Fusion, Safety Events, and Persistence

## 1. Goal

Combine sensor and video predictions into one trustworthy activity stream, detect safety events with false-alarm controls, store history, and expose live/history interfaces for the later dashboard.

## 2. User value

- Caregivers receive one clear activity instead of two conflicting labels.
- Falls are treated as critical only when the required sensor and video evidence agree.
- Doctors and later UI features can read persisted activity and event history.
- Recognition continues in a visible degraded mode if one modality disappears.

## 3. Requirements

| Source ID | Priority | Behaviour | Acceptance |
|---|---|---|---|
| FR-F1 | Must | Align both modality predictions by time and output one activity per interval. | Each interval produces one canonical activity and contributor information. |
| FR-F2 | Must | Use configurable confidence-weighted voting. | Higher weighted evidence wins in deterministic disagreement tests. |
| FR-F3 | Must | Smooth recent decisions. | One noisy interval does not immediately change a stable label. |
| FR-F4 | Must | Raise a fall only for motion spike AND horizontal body within tolerance. | Fall scenario produces one event; ordinary lying and one-sided evidence do not produce a critical fall. |
| FR-F5 | Must | Persist and publish activity/events. | Records survive restart and valid MQTT/WS consumers receive them. |
| FR-F6 | Should | Detect inactivity and abnormal pattern. | Configured prolonged stillness raises one inactivity event. |
| FR-F7 | Should | Continue using an available modality. | Sensor-only and video-only modes produce activity with degraded health. |
| FR-X1 | Must | Preserve timeline and events locally. | History is returned after service restart. |

## 4. Core behaviours

### Normal activity

Fusion matches nearby sensor and video messages, scores candidate labels, smooths the winner, stores it, and broadcasts the result. Contributors show which labels supported the decision.

### Fall event

A fall requires high sensor motion and video becoming horizontal inside a short configured window. The system writes one `FALL` event with `critical` severity and evidence. A cooldown/deduplication rule prevents repeated alerts for the same fall.

### Degraded mode

If either modality is stale, Fusion uses the fresh source and marks the missing source offline. A single source may report activity, but it must not create the normal high-confidence two-source fall alert unless a separately documented degraded safety policy is enabled.

### History and acknowledgement

Clients can request current status, timeline, trends, and events by time range. Alert acknowledgement marks an event as seen without deleting or changing its original evidence.

## 5. API acceptance

- `GET /api/status` returns activity, confidence, modality health, and last update.
- `GET /api/timeline?from=&to=` returns ordered persisted activity.
- `GET /api/trends?period=` returns durations/counts suitable for charts.
- `GET /api/events?from=&to=` returns ordered safety events.
- `POST /api/events/{id}/ack` is idempotent and returns not-found for an unknown ID.
- `/ws` broadcasts typed `activity` and `event` envelopes.

## 6. Non-functional expectations

- Activity target latency is below one second where local hardware permits; fall banner consumers receive an event within about 1-2 seconds.
- Duplicate, late, and out-of-order messages do not crash the service.
- Database or broker failure is logged and surfaced in health.
- Tunable weights and thresholds require no code changes.

## 7. Exit checklist

- [ ] Agreement and disagreement fusion tests pass.
- [ ] Smoothing rejects isolated label flicker.
- [ ] Acted/simulated fall creates exactly one persisted event.
- [ ] Ordinary sitting/lying and one-modal evidence do not create a critical fall.
- [ ] Inactivity scenario works at a shortened test threshold.
- [ ] Each single-modality failure mode continues safely.
- [ ] REST, WebSocket, MQTT, and database integration tests pass.
- [ ] Restart preserves history and acknowledgement.

