# Milestone 5 implementation notes

Milestone 5 turns the implemented HAR prototype into a repeatable, auditable release candidate. It
does not make a result true merely by supplying a checklist: every measured claim must link to an
artifact captured from the exact commit and frozen configuration under test.

## Delivered verification and release controls

- The metrics harness under `tests/metrics/` evaluates sensor-only, video-only, raw fusion, and
  smoothed fusion outputs against ground truth kept outside inference messages. Its outputs include
  machine-readable run metadata and a Markdown summary. Run a captured scenario with
  `uv run python -m tests.metrics <scenario.json> --output-dir <artifact-directory>`.
- Existing Python, dashboard, contract, integration, Compose-build, and infrastructure smoke gates
  remain the baseline. Release-only webcam, model, dataset, LLM, offline, privacy, recovery, soak,
  usability, and metrics checks are recorded separately because CI cannot reproduce the target
  laptop or human observation.
- [RUNBOOK.md](RUNBOOK.md) defines preparation, clean start, expected health, scenario order,
  failure recovery, reset, logs, offline rehearsal, and release tagging.
- [`evidence/`](evidence/README.md) contains immutable-result templates for configuration, metrics,
  privacy, offline behavior, usability, dependencies/licenses, limitations, release gates, and
  requirement traceability.
- Config remains environment-driven through `.env.example`. Freeze a redacted copy or hash for a
  release; never commit a working `.env`, credentials, downloaded datasets, model weights, raw
  sensor windows, or camera content.

## Evidence status

The repository supplies the verification machinery and blank evidence records. Target-laptop
measurements are intentionally marked `NOT RUN` until an operator executes the runbook. Do not
replace that status with `PASS` without recording the command, UTC timestamp, commit, configuration
hash, environment, artifact path, and reviewer.

Milestone 5 passes only if every Must requirement is `PASS`. A failed accuracy, fall, privacy,
offline, reliability, or usability target must remain visible in the report and in
`evidence/known-limitations.md`; a limitation cannot convert a Must failure into a pass.

## Release entry points

From the repository root:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
(cd dashboard && npm ci && npm test && npm run lint && npm run build)
docker compose config --quiet
uv run python scripts/validate_deployment.py
uv run python scripts/release_audit.py --output-dir artifacts/release
./scripts/smoke.sh
```

The smoke script starts and normally stops the stack while retaining named volumes. Set
`SMOKE_REMOVE_VOLUMES=true` only for an intentional disposable clean-state run. Full target-laptop
verification continues with the [demo and operations runbook](RUNBOOK.md).

`tests/metrics/scenarios/release_demo_v1.json` is an illustrative synthetic harness fixture only. Its
values are not target-laptop measurements and must never be cited as final evaluation evidence.

## Tuning and final-evaluation policy

Tune window sizes, modality weights, smoothing, alignment, posture/fall thresholds, and cooldown
only on development or validation scenarios. Before final evaluation:

1. select and record the fixed evaluation scenarios;
2. freeze dependency locks, model identity, dataset version, label mapping, and redacted config hash;
3. record the candidate commit and confirm a clean worktree;
4. run the fixed evaluation once and preserve all outputs;
5. report failures honestly rather than tuning against final results.

This project does not train or fine-tune a model in Milestone 5 and must not claim clinical accuracy
from the academic demonstration.
