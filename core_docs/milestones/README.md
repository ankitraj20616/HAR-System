# Project Milestones

This folder divides the HAR project into five clear milestones. Each milestone should leave the
repository in a working and testable state.

The project is intentionally software-only:

- public datasets act like a wearable motion sensor;
- a normal laptop webcam provides the video stream;
- no physical IoT board is required;
- no custom machine-learning model is trained;
- pre-trained models and deterministic rules are used instead.

## Current progress

| Milestone | Status | Main result |
|---|---|---|
| 1. Foundation and contracts | Implemented | Runnable services, MQTT, PostgreSQL, shared schemas, configuration, health checks |
| 2. Single-modality recognition | Implemented | Dataset replay, sensor activity recognition, webcam pose recognition |
| 3. Fusion, safety, and persistence | Implemented | One activity stream, fall/inactivity events, saved history, REST and WebSocket APIs |
| 4. Dashboard and feedback | Planned | Finished caregiver dashboard, alert UI, GenAI feedback, summaries |
| 5. Verification and release | Planned | Metrics, resilience checks, offline demo, final documentation and release |

“Implemented” means the code and automated tests exist in the development history. A milestone is
fully accepted only after its exit checklist also passes in the intended demo environment.

## What each milestone folder contains

Every milestone has two core documents:

- `FSD.md` — the **Functional Specification Document**. It explains what the user should receive and
  how acceptance is judged.
- `TDD.md` — the **Technical Design Document**. It explains the architecture, algorithms,
  configuration, reliability rules, and tests used to build the feature.

An implemented milestone may also have:

- `IMPLEMENTATION.md` — important decisions, delivered files, behavior, and limitations discovered
  while building it.

Read the FSD first if you want the product view. Read the TDD next if you are implementing or
reviewing the code.

## Milestone 1: Foundation and contracts

Folder: [`milestone-1-foundation`](milestone-1-foundation/)

### Goal

Create a safe base that every later feature can use.

### Main work

- FastAPI service skeletons and health endpoints;
- Mosquitto MQTT broker;
- PostgreSQL database and repeatable SQL schema;
- canonical activity/event labels;
- strict JSON message contracts;
- environment-based configuration;
- structured logs;
- Docker Compose startup and CI checks.

### Main requirements

`FR-X1`, `FR-X3`, `FR-X4`, `NFR-6`, `NFR-9`, and `NFR-10`.

### Completion idea

The stack starts, services report health, MQTT can move a message, PostgreSQL tables exist, and shared
contracts reject invalid data.

## Milestone 2: Single-modality recognition

Folder: [`milestone-2-single-modality`](milestone-2-single-modality/)

### Goal

Make the sensor and video paths work independently before combining them.

### Main work

- UCI HAR, WISDM, and SisFall dataset loaders;
- controllable MQTT sensor replay;
- fixed-size sensor windows and feature extraction;
- pinned local pre-trained model adapter;
- deterministic sensor fallback when the model is unavailable;
- webcam capture and MediaPipe pose landmarks;
- geometric posture and motion rules;
- strict rule that raw video is never stored or transmitted;
- graceful `UNKNOWN` behavior when a person or model cannot be used.

### Main requirements

`FR-S1`–`FR-S6`, `FR-V1`–`FR-V8`, `FR-X2`, and `NFR-3`.

### Completion idea

The Sensor Service publishes a valid sensor prediction, the Video Service publishes a valid video
prediction, and either service can stay alive when its preferred input/model is unavailable.

## Milestone 3: Fusion, safety events, and persistence

Folder: [`milestone-3-fusion-safety`](milestone-3-fusion-safety/)

### Goal

Turn two possibly different predictions into one trustworthy activity result and safe event history.

### Main work

- bounded timestamp-ordered sensor/video buffers;
- duplicate, late, stale, and out-of-order message handling;
- nearest-time alignment;
- configurable confidence × modality-weight voting;
- deterministic tie behavior;
- temporal smoothing so one noisy result does not immediately change the display;
- sensor-only and video-only degraded operation;
- two-signal fall detection;
- fall cooldown, recovery, and deduplication;
- inactivity detection;
- explainable abnormal-pattern baseline;
- idempotent PostgreSQL activity/event storage;
- status, timeline, trend, event, and acknowledgement REST APIs;
- bounded live WebSocket delivery;
- MQTT reconnect and resubscription behavior.

### Main requirements

`FR-F1`–`FR-F7`, `FR-X1`, `NFR-1`, `NFR-2`, and `NFR-4`.

### Important safety rule

A normal critical fall requires both a high-motion sensor signal and horizontal video evidence inside
the configured correlation window. One-sided evidence is not enough.

### Completion idea

Agreement/disagreement fusion tests pass, noisy label flicker is smoothed, a real fall scenario creates
exactly one event, ordinary lying does not create a critical fall, single-modality mode continues, and
saved history survives service restart.

Implementation details are recorded in
[`milestone-3-fusion-safety/IMPLEMENTATION.md`](milestone-3-fusion-safety/IMPLEMENTATION.md).

## Milestone 4: Dashboard and GenAI feedback

Folder: [`milestone-4-dashboard-feedback`](milestone-4-dashboard-feedback/)

### Goal

Give caregivers and doctors a simple user interface and understandable feedback.

### Planned work

- live current-activity card;
- modality/service health panel;
- clear critical fall banner;
- timeline and event history;
- trend charts;
- event acknowledgement in the UI;
- local LLM or template-backed feedback;
- alert text and periodic summaries;
- structured output with a safety disclaimer;
- fallback behavior when the LLM is unavailable.

### Main requirements

`FR-D1`–`FR-D7`, `FR-G1`–`FR-G6`, `NFR-5`, `NFR-8`, and `NFR-11`.

### Completion idea

A non-technical user can understand the current activity, see a fall clearly, review history, and read
plain-language feedback that never claims to diagnose a medical condition.

## Milestone 5: Verification and release

Folder: [`milestone-5-verification-release`](milestone-5-verification-release/)

### Goal

Prove that the complete system is reliable enough for the college demonstration and final report.

### Planned work

- labeled dataset replay through the full pipeline;
- per-class F1 scores;
- fall precision and recall;
- end-to-end latency measurements;
- fusion-versus-single-modality comparison;
- broker/database/camera failure tests;
- offline demonstration checks;
- privacy and dependency audit;
- final setup, troubleshooting, and report documentation;
- release tags.

### Main requirements

`FR-X3`–`FR-X5` and the complete project acceptance checklist.

### Completion idea

One documented command starts the demo, expected safety and resilience scenarios pass, metrics are
available for the final report, and another person can follow the documentation without help from the
original developers.

## Requirement code guide

The short requirement IDs come from the approved project specification:

| Prefix | Area |
|---|---|
| `FR-S` | Sensor Service |
| `FR-V` | Video Service |
| `FR-F` | Fusion Service |
| `FR-G` | GenAI Feedback Service |
| `FR-D` | Dashboard |
| `FR-X` | Cross-cutting platform requirement |
| `NFR` | Non-functional requirement such as privacy, reliability, or latency |

The full definitions are in [`../FUNCTIONAL_SPEC.md`](../FUNCTIONAL_SPEC.md). Engineering details are
in [`../TECHNICAL_DESIGN.md`](../TECHNICAL_DESIGN.md).

## Rules for completing a milestone

A milestone should be called complete only when:

1. all “Must” requirements in its FSD are implemented;
2. its unit, contract, and integration tests pass;
3. configuration is documented and does not require source-code edits;
4. privacy and safety rules are preserved;
5. failures degrade safely instead of crashing the whole system;
6. the milestone exit checklist passes on a fresh checkout;
7. the changes are reviewed before merging into the shared development branch.

## Shared rules across every milestone

- Use only these activity labels: `WALKING`, `SITTING`, `STANDING`, `LYING`, `EXERCISING`,
  `UNKNOWN`.
- Use only these event labels: `FALL`, `INACTIVITY`, `ABNORMAL_PATTERN`.
- Never store, encode, log, or publish raw webcam frames.
- Never put dataset ground truth inside inference MQTT messages.
- Keep model names, thresholds, ports, and timing values configurable.
- Do not log sensor windows, secrets, database URLs, or API keys.
- Prefer local and open-source operation. Cloud providers are optional and must not block the local
  demo.
- Add tests for normal behavior, invalid input, missing dependencies, duplicate messages, and restart
  behavior.

## Branch and tag guidance

Work is developed on short-lived feature branches and integrated into the shared development branch
after review. The detailed rules are in [`../BRANCHING_STRATEGY.md`](../BRANCHING_STRATEGY.md).

Suggested accepted milestone tags are:

- `v0.1-m1`
- `v0.2-m2`
- `v0.3-m3`
- `v0.4-m4`
- `v1.0-demo` or `v1.0-submission`
