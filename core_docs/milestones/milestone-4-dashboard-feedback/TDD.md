# Milestone 4 TDD: Caregiver Dashboard and GenAI Feedback

## 1. Architecture

Use a React + Vite SPA with Recharts. REST loads status/history/trends/events/feedback; WebSocket supplies live activity, event, and feedback envelopes. The Feedback Service subscribes to events, reads PostgreSQL timeline summaries, invokes a provider adapter, validates structured output, persists it, and publishes it.

## 2. Dashboard component design

`App` coordinates routing and a central server-state layer. Components: `StatusBar`, `FallAlertBanner`, `LiveMonitor`, `ActivityTimeline`, `TrendsPanel`, `AIFeedbackPanel`, and `AlertsLog`.

REST client must use typed response models, timeouts, cancellation, and readable errors. WebSocket client uses reconnect with capped exponential backoff, prevents duplicate handlers, records last-message time, and refreshes REST state after reconnect to fill gaps.

Keep critical event state separate from transient toast notifications. Calculate timeline durations from consecutive entries with a defined end-time policy. Charts must include labels/tooltips and a non-chart text/table alternative where practical.

## 3. Feedback Service design

Provider interface: `generate(mode, digest) -> Feedback`. Default adapter calls local Ollama; optional Gemini/OpenAI/Anthropic adapters are selected by `LLM_PROVIDER`. Cloud keys are environment-only and cloud mode is explicitly non-offline.

Build a compact digest containing time range, activity durations, transitions, and factual events. Do not send raw landmarks, raw sensor arrays, or raw frames. System prompt requires plain language, no diagnosis, supplied-facts-only content, safe action wording, and a disclaimer.

Validate `headline`, `detail`, severity enum, bounded recommendation list, and non-empty disclaimer with Pydantic. Reject/repair invalid output once, then use a deterministic template. For critical events, publish template alert immediately so slow LLM inference cannot delay safety notification.

## 4. Feedback modes

- Alert: event type, detected time, confidence/evidence summary, immediate general action, disclaimer.
- Feedback: recent activity distribution and balanced, non-clinical suggestions.
- Summary: selected-period facts, notable events, unknown-data caveat, disclaimer.

Persist the complete validated payload. Use request/event IDs for idempotency so reconnects do not generate duplicate alert feedback.

## 5. API and configuration

Consume Milestone 3 endpoints and add `GET /api/feedback/latest`, `POST /api/feedback/generate`, and feedback WebSocket/MQTT publication. Validate requested period and mode; return explicit 4xx errors for bad input and 503/fallback metadata for provider problems.

Variables include `LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_HOST`, provider API keys, generation timeout, feedback interval, summary schedule, maximum digest size, and fallback flag.

## 6. Tests

- UI unit tests for every loading, empty, error, stale, critical, and acknowledged state.
- API/WebSocket tests including reconnect and duplicate event handling.
- Feedback schema and provider-adapter tests with mocked providers.
- Safety tests for disclaimer, forbidden diagnostic language, unsupported claims, invalid JSON, timeout, and offline fallback.
- End-to-end browser flow: live update → fall banner → alert details → acknowledgement → feedback panel.
- Basic accessibility checks for keyboard focus, semantic headings, alert role/live region, contrast, and chart labels.

## 7. Branch plan and release

- `feat/dashboard-live-monitor`
- `feat/dashboard-timeline-trends`
- `feat/dashboard-alerts-health`
- `feat/feedback-ollama-provider`
- `feat/feedback-structured-prompts`
- `test/feedback-safety-cases`

Tag accepted completion `v0.4-m4`.

