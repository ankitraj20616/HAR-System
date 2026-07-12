# Privacy evidence checklist

**Status:** `NOT RUN`  
**Commit/config hash:** `PENDING`  
**UTC time / auditor role:** `PENDING`  
**Audit command/version and artifact:** `PENDING`

Record the path/query inspected, method, result count, and a sanitized artifact for every row. Do
not copy prohibited material into evidence merely to prove it existed; quarantine the environment,
record metadata, and mark the Must requirement failed.

| Check | Acceptance | Status | Evidence / notes |
|---|---|---|---|
| Video pipeline source review | Frames remain in memory and are not encoded/written/published | `NOT RUN` | `PENDING` |
| MQTT topics/payload schemas | No bytes/base64/image/path fields; only approved numeric/derived data | `NOT RUN` | `PENDING` |
| PostgreSQL schema and sampled rows | No frame/image/blob/path content in activity, event, or feedback data | `NOT RUN` | `PENDING` |
| PostgreSQL named volume | No image/video files or unintended exports | `NOT RUN` | `PENDING` |
| Mosquitto data volume | No retained raw frame/image payload | `NOT RUN` | `PENDING` |
| Service and Compose logs | No raw frames, raw sensor windows, landmarks, secrets, URLs with credentials, or personal data | `NOT RUN` | `PENDING` |
| Generated metrics/report artifacts | No camera content, personal data, credentials, or inference input leakage | `NOT RUN` | `PENDING` |
| Dashboard screenshots | Derived state only; no raw camera, names, medical details, secrets, or sensitive paths | `NOT RUN` | `PENDING` |
| Feedback/LLM digest and output | Aggregated activity/events only; no raw windows/landmarks/frames; safe disclaimer present | `NOT RUN` | `PENDING` |
| Network observation | Raw frames are not transmitted from Video Service | `NOT RUN` | `PENDING` |
| Repository secret/prohibited-file scan | No committed secrets, `.env`, models/datasets, DB dumps, images, or videos | `NOT RUN` | `PENDING` |

**Raw video persisted or transmitted count:** `PENDING` (acceptance requires zero)  
**Finding owner/remediation/retest:** `PENDING`  
**Reviewer sign-off:** `PENDING`

