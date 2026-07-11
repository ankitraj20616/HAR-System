# Release checklist

**Release candidate:** `PENDING`  
**Overall status:** `NOT RUN`  
**Release owner / reviewer roles:** `PENDING`

## Freeze and gates

- [ ] Candidate commit recorded and `git status --short` empty.
- [ ] Fixed evaluation scenarios, mapping, tolerances, and averaging policy recorded.
- [ ] Dependencies, image digests, datasets, models, and redacted config/hash frozen.
- [ ] No tuning was performed against the final evaluation result.
- [ ] Python format, lint, unit, contract, integration, and metrics tests pass.
- [ ] Dashboard tests, type/lint check, and production build pass.
- [ ] Compose validation, application image build, and smoke test pass.
- [ ] Release audit reports no exposed secret/prohibited artifact; every license is resolved.
- [ ] Expected-rate load/soak result shows bounded queues and acceptable memory behavior.

## Target-laptop evidence

- [ ] Clean checkout preparation and clean start completed using only the runbook.
- [ ] Expected health and both-modality-online state recorded.
- [ ] Normal, unknown/no-person, true-fall, and every false-alarm control recorded.
- [ ] Exactly one prompt alert observed for the agreed true-fall scenario.
- [ ] Feedback/summary relevance, schema, disclaimer, and provider fallback verified.
- [ ] Camera, sensor, broker, DB, LLM, and browser failure/recovery tests recorded.
- [ ] Persistence survives non-volume restart, including feedback and acknowledgement state.
- [ ] Metrics report includes all required metadata/results and fusion/fall targets pass.
- [ ] Privacy audit passes with zero persisted/transmitted raw frames.
- [ ] Complete demo passes offline after documented preparation.
- [ ] Untrained caregiver usability acceptance passes.
- [ ] Known limitations reviewed and no failed/blocked Must remains.
- [ ] Requirement traceability has an artifact and reviewer for every Must.

## Demo and submission tags

- [ ] Exact demo rehearsal completed from clean checkout.
- [ ] `v1.0-demo` is annotated and points to the reviewed demo commit.
- [ ] Report/PPT-only references complete without changing tested behavior.
- [ ] Final smoke and affected audit/document checks pass on submitted state.
- [ ] `v1.0-submission` is annotated and points to the exact submitted commit.
- [ ] Tag objects, commits, UTC timestamps, and reviewer sign-off recorded below.

| Item | Commit/tag object | UTC timestamp | Reviewer | Artifact/status |
|---|---|---|---|---|
| Demo candidate | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |
| Submission candidate | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` |

Do not push a tag unless the release owner authorizes the external state change.

