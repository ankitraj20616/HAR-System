# Milestone 4 FSD: Caregiver Dashboard and GenAI Feedback

## 1. Goal

Turn the working recognition pipeline into a simple caregiver/doctor experience. Users see live status, prominent safety alerts, history and trends, plus structured plain-English feedback that never claims to diagnose.

## 2. Personas and outcomes

- Caregiver: sees current activity and urgent fall alerts at a glance.
- Doctor/reviewer: checks timeline, trends, and a concise period summary.
- Admin: sees which service/modality is online and can diagnose a stale stream.
- Patient: benefits from clear response while raw video stays private.

## 3. Dashboard requirements

| Source ID | Priority | Behaviour | Acceptance |
|---|---|---|---|
| FR-D1 | Must | Show current activity live without page reload. | Changes appear in about 1-2 seconds with timestamp/confidence. |
| FR-D2 | Must | Show an unmistakable fall/abnormal alert. | Critical event produces a persistent red banner and readable message. |
| FR-D3 | Must | Show activity timeline with timestamps and durations. | User can read recent ordered history and choose a time range. |
| FR-D4 | Must | Show activity trends. | At least one accessible chart shows time per activity or activity over time. |
| FR-D5 | Must | Show latest feedback and summaries. | Structured fields and disclaimer render reliably. |
| FR-D6 | Should | Show service/modality health. | Offline source is clearly different from healthy and shows last update. |
| FR-D7 | Could | Acknowledge an alert. | Seen alert remains in history and changes visual state. |

## 4. Feedback requirements

| Source ID | Priority | Behaviour | Acceptance |
|---|---|---|---|
| FR-G1 | Must | Produce personalized plain-language feedback from recent activity. | Text refers only to supplied timeline facts and is easy to understand. |
| FR-G2 | Must | Produce concise text for fall/abnormal events. | Output states what was detected, when, severity, and a safe next step. |
| FR-G3 | Should | Produce daily/periodic summaries. | Requested period returns a coherent recap. |
| FR-G4 | Must | Never diagnose and always include a safety disclaimer. | Automated checks and review find disclaimer and no diagnostic claim. |
| FR-G5 | Must | Return predictable structured output. | `headline`, `detail`, `severity`, `recommendations`, and `disclaimer` validate. |
| FR-G6 | Should | Work offline after initial model download. | Ollama path works with networking disabled. |

## 5. Main user journeys

### Live monitoring

User opens the app, sees current activity and system health, and receives WebSocket updates. Reconnection must happen automatically and the page must show when displayed data is stale.

### Fall response

A critical event immediately shows a dominant banner. Template text is available immediately; LLM-enhanced text may replace/add detail when ready. User opens the alert record and may acknowledge it. Acknowledgement never means the patient is safe; it only means the message was seen.

### Review and feedback

User selects a period, views its timeline/trends, requests feedback or a summary, and reads recommendations plus disclaimer. Empty periods show a helpful empty state rather than invented activity.

## 6. UX and safety rules

- Use large labels, plain words, visible timestamps, and text/icons in addition to color.
- Critical alerts remain visible until acknowledged or explicitly dismissed according to policy.
- Never hide degraded modality status behind an overall green state.
- AI content is assistive, not medical advice. It must not invent patient identity, vital signs, causes, injuries, or diagnoses.
- If the LLM fails or returns invalid JSON, show safe deterministic fallback text.

## 7. Exit checklist

- [ ] Live activity updates without reload and recovers after WebSocket reconnect.
- [ ] Fall event creates a clear banner and alert record.
- [ ] Timeline, time filter, trends, feedback, and summary views work.
- [ ] Offline/degraded health and stale-data states are visible.
- [ ] Alert acknowledgement is persisted and idempotent.
- [ ] Feedback schema, disclaimer, grounding, and fallback tests pass.
- [ ] Keyboard navigation, readable contrast, loading/error/empty states are checked.
- [ ] Local Ollama demo runs offline.

