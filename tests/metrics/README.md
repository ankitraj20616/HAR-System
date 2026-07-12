# HAR metrics harness

Run the illustrative fixed fixture with:

```bash
uv run python -m tests.metrics tests/metrics/scenarios/release_demo_v1.json \
  --output-dir artifacts/metrics
```

The command prints the Markdown summary and writes `metrics.json`, `metrics.csv`,
and `summary.md`. The bundled `release_demo_v1.json` exists to verify evaluator
math and report generation. Its predictions are illustrative fixed values, **not
measured model evidence**, and must not be quoted as final system performance.
Replace it with the frozen release capture before producing report evidence.

Each sample keeps `ground_truth` separate from sensor, video, raw-fused, and
smoothed-fused predictions and records `source_ts` plus the dashboard-receivable
`websocket_ts`. Each event requires a canonical `type`; only `FALL` events enter
fall scoring. `INACTIVITY` and `ABNORMAL_PATTERN` remain valid capture records but
are excluded. Fall matching selects the nearest eligible pairs globally within
`config.fall_match_tolerance_seconds`; one truth and one prediction may each be
used once. Extra in-tolerance alerts count both as false positives and duplicates.

The averaging policy is fixed: per-class zero-division results are zero, macro F1
includes all six canonical classes, and weighted F1 uses ground-truth support.
Latency p95 uses linear interpolation at rank `(n - 1) * 0.95`.

For final evidence, pass a frozen capture from the exact release commit and configuration, then link
the generated artifacts from
[`core_docs/milestones/milestone-5-verification-release/evidence/verification-report.md`](../../core_docs/milestones/milestone-5-verification-release/evidence/verification-report.md).
