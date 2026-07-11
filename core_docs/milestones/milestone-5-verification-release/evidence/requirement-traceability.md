# Milestone 5 requirement traceability

**Overall status:** `NOT RUN`

Rows below identify the planned procedure and evidence record. An implementation path is not proof
of acceptance. Update status only after linking the candidate-specific artifact.

| Requirement | Priority | Acceptance and verification path | Evidence record/artifact | Status |
|---|---|---|---|---|
| FR-X3 | Must | Clean target laptop follows prerequisites; documented start brings up the agreed demo stack; replay mode is documented and exercised | `RUNBOOK.md` sections 1–4; clean-start log | `NOT RUN` |
| FR-X4 | Should | Change one approved threshold/model/provider setting through `.env`, restart, and observe reported behavior/config identity without source edit | Frozen redacted config/hash; verification report | `NOT RUN` |
| FR-X5 | Should | Fixed labeled replay produces per-class/aggregate F1, fall precision/recall, latency, and run metadata in machine/human-readable forms | Metrics output directory; verification report | `NOT RUN` |
| NFR-1 | Must | Measure source/event-to-dashboard-receivable latency distribution; activity target `<1 s`, fall about `1–2 s` | Verification report latency table/raw samples | `NOT RUN` |
| NFR-2 | Must | Same agreed evaluation shows fusion F1 above both single modalities and fall precision/recall about `0.9`; false-alarm controls included | Metrics summary/confusion matrix/fall matches | `NOT RUN` |
| NFR-3 | Must | Audit code, messages, DB, volumes, logs, generated artifacts, screenshots and network observation; zero persisted/transmitted raw frames | `privacy-checklist.md` and audit output | `NOT RUN` |
| NFR-4 | Must | Stop sensor and video independently; unaffected modality continues, state degrades explicitly, and recovery succeeds without crash | Verification report reliability table/logs | `NOT RUN` |
| NFR-5 | Must | Untrained caregiver identifies live state and fall alert unaided and can find acknowledgement/history | `usability-notes.md` | `NOT RUN` |
| NFR-6 | Must | Agreed stack and fixed scenarios run on recorded standard-laptop hardware using documented start | Verification report run identity/start log | `NOT RUN` |
| NFR-7 | Must | Complete dependency/model/dataset audit finds no required paid/closed component and licenses are approved | `dependency-inventory.md` | `NOT RUN` |
| NFR-8 | Must | After online preparation, complete agreed demo while external networking is demonstrably disabled and no runtime download occurs | `offline-checklist.md` | `NOT RUN` |
| NFR-9 | Must | Architecture remains isolated and important thresholds/models/providers change through configuration | Config test, `.env.example`, design review artifact | `NOT RUN` |
| NFR-10 | Must | Failure scenarios produce safe structured lifecycle/dependency/prediction/event diagnostics without sensitive payloads | Sanitized logs plus privacy/recovery results | `NOT RUN` |
| NFR-11 | Must | Generated and fallback feedback contain disclaimer, avoid diagnoses/unsupported claims, and do not delay deterministic fall alerting | Automated safety tests plus demo feedback artifact | `NOT RUN` |

## Final demo acceptance

| Acceptance observation | Evidence | Status |
|---|---|---|
| Broker, DB, services, dashboard, and documented simulator mode start as approved | `PENDING` | `NOT RUN` |
| Both modality indicators become online | `PENDING` | `NOT RUN` |
| Activity changes and persists to history/trends | `PENDING` | `NOT RUN` |
| One safe acted/simulated fall creates exactly one prompt alert | `PENDING` | `NOT RUN` |
| Sitting/lying false-alarm control creates no critical fall | `PENDING` | `NOT RUN` |
| Feedback and summary are relevant, structured, safe, and disclaimed | `PENDING` | `NOT RUN` |
| Video shutdown leaves sensor-only activity operational | `PENDING` | `NOT RUN` |
| Restart retains timeline, events, feedback, and acknowledgements | `PENDING` | `NOT RUN` |
| Metrics meet targets or accurately expose a release-blocking Must failure | `PENDING` | `NOT RUN` |
| Offline and privacy audits pass | `PENDING` | `NOT RUN` |

**Must requirements all pass:** `NOT RUN`  
**Reviewer and UTC sign-off:** `PENDING`

