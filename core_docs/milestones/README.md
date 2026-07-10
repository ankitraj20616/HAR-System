# Five-Milestone Delivery Plan

This folder converts the approved project FSD, TDD, and Git branching strategy into five buildable milestones. The scope remains software-only: no physical IoT hardware and no custom model training.

## Milestone map

| Milestone | Main outcome | Source roadmap phases | Main requirements |
|---|---|---|---|
| 1. Foundation and contracts | Runnable project skeleton, MQTT, PostgreSQL, shared schemas, configuration, CI | 1-2 and infrastructure part of 7 | FR-X1, FR-X3, FR-X4; NFR-6, NFR-9, NFR-10 |
| 2. Single-modality recognition | Dataset simulator, sensor recognition, webcam pose recognition | 3-5 | FR-S1-S6, FR-V1-V8, FR-X2; NFR-3 |
| 3. Fusion, safety events, persistence | One authoritative activity stream, fall/inactivity events, history APIs | 6 and remaining part of 7 | FR-F1-F7, FR-X1; NFR-1, NFR-2, NFR-4 |
| 4. Dashboard and GenAI feedback | Caregiver UI, alerts, trends, structured feedback and summaries | 8-9 | FR-D1-D7, FR-G1-G6; NFR-5, NFR-8, NFR-11 |
| 5. Verification and release | Metrics, resilience, offline demo, documentation and final tags | 10 | FR-X3-FR-X5 and all project acceptance criteria |

## Directory structure

Each milestone has an `FSD.md` explaining what users and stakeholders receive, and a `TDD.md` explaining how the team will build and verify it.

## Rules used across all milestones

- `main` must always run. Work is done on short-lived branches and merged through reviewed pull requests.
- Use one focused feature per branch. Suggested branches are included in each TDD.
- Changes to `shared/` contracts need two reviewers because they affect several services.
- Every pull request must mention the relevant `FR-*` or `NFR-*` IDs and include tests.
- Activity labels are fixed: `WALKING`, `SITTING`, `STANDING`, `LYING`, `EXERCISING`, `UNKNOWN`.
- Event types are fixed: `FALL`, `INACTIVITY`, `ABNORMAL_PATTERN`.
- Raw video must never be stored or transmitted.
- Local, open-source choices are the default path for the offline demo. Cloud model providers are optional and must not block local operation.

## Definition of milestone completion

A milestone is complete only when its Must requirements and exit checklist pass on a fresh checkout. Tag accepted milestones as `v0.1-m1`, `v0.2-m2`, `v0.3-m3`, `v0.4-m4`, and finally `v1.0-demo` / `v1.0-submission`.

