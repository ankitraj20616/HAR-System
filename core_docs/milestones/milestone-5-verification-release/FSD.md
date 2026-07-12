# Milestone 5 FSD: Verification, Hardening, and Final Release

## 1. Goal

Prove that the complete project meets its functional, safety, privacy, performance, reliability, offline, and usability promises. Produce a repeatable single-laptop demonstration and evidence suitable for the final report.

## 2. In scope

- Metrics harness for sensor-only, video-only, and fusion results.
- Fall precision/recall and end-to-end latency measurement.
- Full acceptance, failure recovery, privacy, AI safety, usability, and offline tests.
- Docker and webcam fallback runbooks, dataset/model preparation, demo script, report evidence, release tags.
- Bug fixing and threshold/config tuning using validation evidence; no custom model training.

## 3. Requirements

| Source | Priority | Required result | Acceptance |
|---|---|---|---|
| FR-X3 | Must | One documented command starts the demo stack. | Fresh laptop setup follows only the written prerequisites and command. |
| FR-X4 | Should | Important settings remain config-driven. | Test changes thresholds/model/provider without source edit. |
| FR-X5 | Should | Metrics are reproducible. | Command prints per-class/aggregate F1, fall precision/recall, latency, and run metadata. |
| NFR-1 | Must | Real-time experience. | Activity target below 1 s and fall display about 1-2 s, with measured distribution. |
| NFR-2 | Must | Fusion improves recognition and fall quality is high. | Fusion F1 exceeds both single modalities on the agreed evaluation; fall precision and recall target about 0.9. |
| NFR-3 | Must | Raw-video privacy. | Audit finds no persisted/transmitted raw frames. |
| NFR-4 | Must | Degraded operation. | Removing either modality does not crash the system. |
| NFR-5 | Must | Caregiver usability. | A test user identifies live state and fall alert without training. |
| NFR-6-NFR-8 | Must | Laptop, license/cost, and offline readiness. | Approved local stack runs offline after preparation with no paid dependency required. |
| NFR-10-NFR-11 | Must | Useful logs and safe AI output. | Failures can be traced; all displayed AI output is non-diagnostic and disclaimed. |

## 4. Evaluation scenarios

1. Normal walking, sitting, standing, lying, exercising, and unknown/no-person periods.
2. True fall: motion spike followed by horizontal posture.
3. False-alarm controls: ordinary lying, vigorous motion while upright, horizontal posture without spike.
4. Sensor missing, video missing, broker restart, DB restart, LLM unavailable, browser reconnect.
5. Full offline run after images/models/datasets have been prepared.

## 5. Metrics report rules

Report dataset/version, scenario selection, mapping, thresholds, hardware, software versions, sample count, and timestamp. Show per-class precision/recall/F1, macro and weighted F1, confusion matrix, fall event precision/recall/F1, duplicate alerts, and latency median/p95/max. Do not claim clinical accuracy from a small academic demo.

If fusion does not beat both modalities, the milestone is not passed. The report must show the result honestly; adjust documented weights/thresholds or scope claims and rerun on the same fixed evaluation set without training on it.

## 6. Final demo acceptance

- [ ] One command starts broker, DB, services, dashboard, and the documented simulator mode.
- [ ] Both modality health indicators become online.
- [ ] Live activity changes and persists to history/trends.
- [ ] One acted/simulated fall creates exactly one prompt alert.
- [ ] Sitting/lying does not create a false fall.
- [ ] Feedback and period summary are relevant, structured, and disclaimed.
- [ ] Webcam shutdown leaves sensor-only activity running.
- [ ] Restart retains timeline, events, feedback, and acknowledgements.
- [ ] Metrics meet or clearly document every target.
- [ ] Offline and privacy audits pass.

## 7. Release decision

All Must requirements must pass. Any accepted limitation is written in the report and demo notes. Create `v1.0-demo` only after a rehearsal from a clean checkout; create `v1.0-submission` for the exact submitted state.

