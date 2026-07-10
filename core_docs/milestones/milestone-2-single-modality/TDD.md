# Milestone 2 TDD: Sensor and Video Recognition

## 1. Components

Implement `simulator/replay.py`, dataset loaders, `sensor_service`, and `video_service`. Both services publish through Mosquitto and import shared enums/schemas rather than duplicating contracts.

## 2. Simulator design

Load UCI HAR by default; make loaders implement a common iterator returning timestamp, sampling rate, accel array, gyro array, source label, and scenario ID. Map UCI walking variants to `WALKING`, `LAYING` to `LYING`, exact sitting/standing labels directly, and unmapped values to `UNKNOWN`.

Replay options should include dataset path, real-time/speed factor, loop, scenario filter, and device ID. Use a monotonic clock for pacing and UTC for message timestamps. Keep ground truth in a separate metrics channel/file so prediction consumers cannot accidentally use it.

## 3. Sensor Service pipeline

1. Validate `har/sensor/raw`.
2. Normalize units and reject non-finite values.
3. Form 1-2 second sliding windows, default 128 samples and 50% overlap.
4. Calculate mean, standard deviation, min/max, signal magnitude area, energy, axis correlations, magnitudes, and tilt values.
5. Run the pinned pre-trained HAR model with its required preprocessing.
6. Map its output to canonical labels and calculate a 0-1 confidence.
7. Calculate motion intensity from acceleration magnitude peak or a normalized equivalent.
8. Publish `SensorPrediction`.

Model adapters isolate HuggingFace-specific input/output details. On model load/inference failure, switch to deterministic thresholds only when `USE_FALLBACK=true`; otherwise publish health failure and `UNKNOWN` safely. Pin the exact model ID/revision and record its license and input assumptions.

## 4. Video Service pipeline

OpenCV captures the configured camera at a target 12 FPS. MediaPipe Pose is the default local choice. Calculate angles with a reusable three-point angle function and guard against missing/low-visibility landmarks.

Use torso shoulder-to-hip angle for orientation; hip and knee flexion plus normalized body height for sitting/standing; a short landmark history for walking and exercise. `LYING` requires horizontal torso evidence. Confidence combines landmark visibility, rule distance from threshold, and temporal consistency.

Frames exist only inside the capture/inference loop. Do not call image writers, encode frames into messages, put frame bytes in logs, or define an image database field. Release the camera cleanly on shutdown and retry connection with capped backoff.

## 5. Configuration

Sensor: `WINDOW_SIZE`, `WINDOW_OVERLAP`, `SENSOR_MODEL_ID`, `SENSOR_MODEL_REVISION`, `USE_FALLBACK`, feature normalization values.

Video: `CAMERA_INDEX`, `FPS`, `MIN_VISIBILITY`, `HORIZONTAL_ANGLE_THRESHOLD`, posture angle thresholds, motion-history length. Validate ranges on startup.

## 6. Testing

- Simulator: pacing, mapping, loop/stop, malformed files, deterministic scenarios.
- Sensor unit: each feature formula, overlap boundaries, model mapping, confidence bounds, calm vs spike intensity.
- Video unit: synthetic landmark geometry for sitting/standing/lying; missing landmarks; threshold edges.
- Contract: published payloads match shared schemas.
- Integration: replay-to-sensor MQTT flow and webcam/video-file test-double-to-video flow.
- Privacy: scan generated files, DB schema, MQTT payloads, and logs for image/frame data.

## 7. Branch plan

- `feat/sim-dataset-replay`
- `feat/sensor-feature-pipeline`
- `feat/sensor-har-inference`
- `feat/video-pose-landmarks`
- `feat/video-activity-rules`
- `test/video-privacy-audit`

Tag the accepted milestone `v0.2-m2`.

## 8. Handoff to Milestone 3

Provide recorded prediction fixtures covering agreement, disagreement, missing modality, motion spike, horizontal posture, and ordinary lying. Document observed message frequency and clock behavior so Fusion can select its alignment tolerance.

