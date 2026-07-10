# Milestone 2 implementation notes

This branch implements the single-modality sensor and video deliverables from the milestone FSD/TDD.

## Runtime contracts

- `simulator.replay` publishes only validated `SensorRaw` messages to `har/sensor/raw`.
- The sensor service buffers fixed windows (default 128 samples, 50% overlap), normalizes units,
  rejects non-finite/stale data, extracts statistical/magnitude/tilt features, and publishes
  `SensorPrediction` messages in UTC timestamp order.
- A local `.tflite` model can be enabled with `SENSOR_MODEL_PATH` and its exact
  `SENSOR_MODEL_LABELS` order. No model or dataset is downloaded by a service at runtime. Missing
  artifacts use deterministic fallback rules only when `USE_FALLBACK=true`; otherwise predictions are
  safe `UNKNOWN` values and health is degraded.
- The video service keeps frames inside the capture/inference loop, converts them immediately to
  numeric landmarks, and publishes only `VideoPrediction`. It never calls image writers/encoders,
  includes frames in logs or MQTT, or creates image database fields.

## Clock and frequency observations

Sensor replay pacing uses `time.monotonic()` and a configurable speed factor; message timestamps are
UTC and derive from the dataset window start. The default 128-sample window at 50 Hz spans 2.56 s,
and 50% overlap advances 1.28 s per prediction. Video pacing targets 12 FPS and uses UTC timestamps
at publication time. Fusion should align modalities with a tolerance of at least one sensor advance
interval plus normal MQTT jitter (roughly 1.3 s for the default replay).

## Dataset and evaluation controls

UCI HAR is the default loader. WISDM and SisFall are supported through the same validated window
iterator. Source labels, scenario IDs, and ground truth are kept in an optional JSONL metrics sink;
they are never added to prediction payloads. `ReplayRunner` exposes start/pause/resume/stop for an
admin process, while CLI options provide speed, loop, scenario filtering, and malformed-row policy.

The fixture `tests/fixtures/milestone2_predictions.json` covers agreement, disagreement, missing
video, motion spike, horizontal transition, and ordinary lying for the Milestone 3 fusion handoff.

## Local demo

```bash
docker compose up --build --wait
python -m simulator.replay --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" --realtime --speed 1
```

On Linux, add `-f docker-compose.webcam.yml` to pass `/dev/video0` into the video container. On macOS
or Windows, run the video service on the host with the same environment variables and point it at
the compose MQTT broker. A missing camera is intentionally a degraded, non-crashing condition.

## Verification

The branch includes unit, contract, integration, and privacy tests for window boundaries, feature
math, model/fallback behavior, MQTT payloads, synthetic postures, temporal motion, camera cleanup,
reconnect behavior, replay lifecycle, and raw-frame absence. The expected local result is all tests
passing with the PostgreSQL integration test skipped when no database is available.
