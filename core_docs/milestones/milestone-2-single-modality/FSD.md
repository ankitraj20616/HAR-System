# Milestone 2 FSD: Sensor and Video Recognition

## 1. Goal

Deliver two independent, real-time activity predictions: one from replayed wearable-sensor data and one from a live webcam. Both must use pre-trained inference or deterministic rules; no model is trained by this project.

## 2. In scope

- UCI HAR default replay and a loader path for WISDM/SisFall.
- Sensor windowing, features, pre-trained classifier, label mapping, confidence, motion intensity, and fallback.
- Webcam capture, pre-trained pose landmarks, posture features, geometric activity rules, confidence, orientation, and missing-person handling.
- MQTT publishing through the shared Milestone 1 contracts.
- Privacy audit proving that raw frames are neither stored nor transmitted.

## 3. User-visible outcome

An admin can start a labeled sensor replay and see ordered sensor predictions. A person can change posture in front of the webcam and see video predictions. Both streams show timestamps, canonical labels, confidence, and operational health.

## 4. Requirements

| Source ID | Priority | Required behaviour | Acceptance |
|---|---|---|---|
| FR-X2 | Must | Replay a public dataset in real time without hardware. | Replay can start, pause/stop, preserve ground truth, and publish valid windows. |
| FR-S1-S2 | Must | Ingest accel/gyro data and produce fixed overlapping windows/features. | Continuous replay produces one valid feature set per expected window. |
| FR-S3-S4 | Must | Run a pre-trained classifier and publish canonical label, confidence, and time. | All outputs validate and arrive in timestamp order. |
| FR-S5 | Should | Publish motion intensity. | A high-motion sample scores clearly above a calm sample. |
| FR-S6 | Could | Use a deterministic fallback when the model cannot load. | Disabled model still produces valid output and health reports degraded mode. |
| FR-V1-V4 | Must | Capture webcam, estimate pose, calculate features, and classify posture/activity. | Live demo distinguishes sitting, standing, lying, and basic movement scenarios. |
| FR-V5 | Must | Do not store or send raw frames. | File, DB, logs, and MQTT audit finds no captured images. |
| FR-V6-V7 | Must/Should | Publish prediction, confidence, timestamp, and orientation. | Fusion-compatible messages report horizontal state correctly in lying tests. |
| FR-V8 | Could | Continue when no person is visible. | Emits `UNKNOWN` with low confidence and stays alive. |

## 5. Sensor flow

1. Admin selects a dataset and replay speed.
2. Loader maps source labels to the canonical six labels.
3. Simulator publishes accel/gyro windows with ground truth kept only for evaluation.
4. Sensor Service validates, extracts features, runs inference, and publishes a prediction.
5. If the model is unavailable, configured fallback rules continue the stream.

## 6. Video flow

1. Video Service opens the configured webcam.
2. Each frame is used locally to extract numeric body landmarks.
3. Geometric rules evaluate torso orientation, knee/hip angles, visibility, and motion history.
4. A canonical label, confidence, and `vertical`/`horizontal` orientation are published.
5. The frame is immediately discarded.

## 7. Behaviour and edge cases

- Missing or corrupt sensor samples are rejected with a reason; the process continues with the next window.
- Unmapped dataset/model classes become `UNKNOWN`.
- Low landmark visibility lowers confidence or produces `UNKNOWN`.
- Webcam disconnect reports unhealthy/degraded status and retries without crashing other services.
- Walking and exercising require short motion history; a single frame must not claim reliable dynamic activity.
- Ground truth is evaluation metadata and must never be presented as the prediction.

## 8. Quality targets

- Video is processed around 10-15 FPS when the laptop can support it.
- Sensor windows default to 128 samples with 50% overlap, configurable without code edits.
- Prediction messages stay within the shared schema.
- Raw-video privacy requirement NFR-3 is mandatory even during debugging.

## 9. Exit checklist

- [ ] UCI HAR replay works end-to-end through MQTT.
- [ ] Sensor output covers all mapped activity classes and includes motion intensity.
- [ ] Model-unavailable scenario is handled clearly.
- [ ] Webcam pose output distinguishes required demo postures.
- [ ] Empty frame produces `UNKNOWN` without a crash.
- [ ] Horizontal orientation is demonstrated.
- [ ] Privacy audit confirms no raw images outside process memory.
- [ ] Unit, contract, and per-modality integration tests pass.

