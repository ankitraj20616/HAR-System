# Milestone 5 evidence package

This directory is the index and set of blank records for final verification. Templates are not test
results. The checked-in default is `NOT RUN`; an operator must attach reproducible evidence before
changing a row to `PASS` or `FAIL`.

## Result vocabulary

| Status | Meaning |
|---|---|
| `PASS` | The stated acceptance criterion was observed on the recorded commit/config/environment and an artifact is linked. |
| `FAIL` | The criterion was executed and was not met; preserve the result and record impact. |
| `BLOCKED` | The check could not run; record the concrete blocker and owner. This is not a pass. |
| `NOT RUN` | No valid result has been recorded for the release candidate. |

## Package inventory

| Record | Purpose | Initial status |
|---|---|---|
| [verification-report.md](verification-report.md) | Run identity, metrics/result links, latency and recovery summary | `NOT RUN` |
| [privacy-checklist.md](privacy-checklist.md) | Raw-frame, payload, storage, log, and artifact audit | `NOT RUN` |
| [offline-checklist.md](offline-checklist.md) | Local HAR processing with authentication dependency/scope recorded | `NOT RUN` |
| [usability-notes.md](usability-notes.md) | Unprompted caregiver walkthrough observations | `NOT RUN` |
| [dependency-inventory.md](dependency-inventory.md) | Runtime/build dependencies, sources, licenses, cost and offline status | `NOT RUN` |
| [known-limitations.md](known-limitations.md) | Accepted constraints and open failures without hiding Must results | Review required |
| [requirement-traceability.md](requirement-traceability.md) | FR/NFR acceptance-to-artifact map | `NOT RUN` |
| [release-checklist.md](release-checklist.md) | Clean checkout, gates, rehearsal, tag and submission approvals | `NOT RUN` |

Generated metrics JSON/CSV/Markdown, confusion matrices, screenshots, logs, inventories, and hashes
may be stored in a separate report-artifact directory. Link immutable paths or checksums here. Do not
commit downloaded datasets/models, `.env`, secrets, database volumes, raw sensor windows, raw video,
or personal data.

## Evidence rules

Every result must identify:

- git commit and dirty/clean state;
- redacted configuration hash and model/dataset versions;
- UTC start/end time, operator/reviewer role, and target hardware/software;
- exact command or manual procedure and fixed scenario IDs;
- observed result, status, and artifact path/checksum;
- deviations, retries, exclusions, and known limitations.

Screenshots may show the dashboard's derived activity/alert state, but not camera frames. A Must
failure remains a release blocker even if it is documented as a known limitation.

For Milestone 6, evidence must additionally record the Supabase project/config identity without
recording keys or tokens, the tested role, expected `401`/`403` results, and the completed
[`SECURITY_CHECKLIST.md`](../../milestone-6-auth-rbac/SECURITY_CHECKLIST.md). Do not paste JWTs,
refresh tokens, service-role keys, confirmation links, or user passwords into evidence artifacts.

“Offline” no longer means that a new user can sign up or log in without Supabase. Record separately:

- local inference, MQTT, persistence and cached-JWKS JWT verification;
- Supabase-dependent signup/login/refresh;
- what happened when the network was removed and whether an already-issued JWT was still valid.

## Generate automated evidence

After `uv sync --frozen`, run the repository gates from the project root:

```bash
uv run python scripts/validate_deployment.py
uv run python scripts/release_audit.py --output-dir artifacts/release
uv run pytest -q tests/unit/test_auth_rbac.py tests/unit/test_auth_tickets.py \
  tests/unit/test_supabase_jwt_verifier.py tests/integration/test_auth_gateway.py
uv run python -m tests.metrics artifacts/captures/final-scenario.json \
  --output-dir artifacts/metrics/final
```

Add `--runtime-path <sanitized-export>` and `--database-url "$DATABASE_URL"` to the release audit
when those prepared target-laptop sources are available. Automated output does not replace the
manual webcam, offline-network, recovery, and usability observations in this directory.
