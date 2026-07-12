# Milestone 4 implementation notes

Milestone 4 delivers the caregiver dashboard and the safety-constrained feedback service.

- `dashboard/` is a React, Vite, TypeScript, and Recharts SPA. It loads authoritative state through
  typed REST clients and listens to separate Fusion and Feedback WebSockets. Both sockets reconnect
  with capped exponential backoff; Fusion reconnection triggers a REST refresh to fill delivery gaps.
- Critical alerts use dedicated state, remain visible across history-filter changes, and clear only
  after a successful idempotent acknowledgement. Stale, offline, loading, empty, and error states are
  visible and accessible. Trend charts include a table alternative.
- Nginx serves the production SPA and provides same-origin routes: Fusion owns `/api/*` and `/ws`,
  while Feedback owns `/api/feedback/*` and `/feedback-ws`.
- `services/feedback_service/` builds compact timeline digests containing durations, transitions, and
  factual events only. Raw sensor arrays, landmarks, and frames never enter LLM prompts.
- The Ollama adapter requests strict JSON. Output is schema-validated and checked for a disclaimer,
  diagnostic language, and unsupported activity/event claims. One repair attempt is allowed before a
  deterministic safe fallback is used.
- Event alerts use deterministic text immediately, so model latency cannot delay safety messaging.
  Feedback persistence supports request/event idempotency keys, and validated payloads are published
  through MQTT and WebSocket.
- Fusion status exposes `current`, `stale`, or `unavailable` data. Timeline durations and trend
  durations are bounded so service downtime is not misrepresented as continuous patient activity.

## Verification

```bash
pytest
ruff check .
ruff format --check .
cd dashboard
npm ci
npm test
npm run lint
npm run build
```

For the local Ollama path, pull the configured model once while online, then run Ollama locally. The
default Compose configuration reaches it at `http://host.docker.internal:11434`. If Ollama is
unavailable or returns invalid/unsafe output, deterministic fallback remains available when
`FEEDBACK_FALLBACK_ENABLED=true`.
