# Offline rehearsal checklist

**Status:** `NOT RUN`  
**Commit/config hash:** `PENDING`  
**Target laptop / UTC interval:** `PENDING`  
**Operator / reviewer role:** `PENDING`

## One-time online preparation

| Check | Status | Evidence / notes |
|---|---|---|
| Container images built and available locally | `NOT RUN` | `PENDING` |
| Python and dashboard dependencies materialized from locks | `NOT RUN` | `PENDING` |
| Approved dataset present and hashed | `NOT RUN` | `PENDING` |
| Pinned sensor model present and hashed, or documented fallback selected | `NOT RUN` | `PENDING` |
| Configured Ollama model present, or deterministic fallback explicitly selected | `NOT RUN` | `PENDING` |
| No runtime download path expected | `NOT RUN` | `PENDING` |

## Disconnected run

Record the safe network-disabling method and evidence that public internet access failed. A browser's
offline indicator alone is insufficient if containers still have external access.

| Check | Status | Evidence / notes |
|---|---|---|
| External network demonstrably unavailable | `NOT RUN` | `PENDING` |
| `docker compose up --no-build --wait` succeeds | `NOT RUN` | `PENDING` |
| Broker, database, services, and dashboard reach documented health | `NOT RUN` | `PENDING` |
| Fixed normal/unknown scenarios complete | `NOT RUN` | `PENDING` |
| False-alarm controls complete | `NOT RUN` | `PENDING` |
| True-fall scenario creates exactly one prompt alert | `NOT RUN` | `PENDING` |
| Feedback/summary is safe and disclaimed (local model or fallback identified) | `NOT RUN` | `PENDING` |
| One-modality degraded operation and recovery complete | `NOT RUN` | `PENDING` |
| Restart preserves timeline/events/feedback/acknowledgement | `NOT RUN` | `PENDING` |
| Logs show no attempted runtime download/cloud dependency | `NOT RUN` | `PENDING` |

**Unexpected DNS/network/download attempts:** `PENDING`  
**Deviation and retest:** `PENDING`  
**Reviewer sign-off and UTC time:** `PENDING`

