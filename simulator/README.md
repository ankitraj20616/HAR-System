# Sensor simulator

The simulator replays public IMU datasets through the shared `SensorRaw` MQTT contract. UCI HAR is
the default format; WISDM raw text and SisFall scenario directories are also supported. Dataset labels
and scenario IDs are written only to an optional ground-truth JSONL file, never to the sensor payload.

```bash
python -m simulator.replay --dataset uci-har \
  --dataset-path "data/UCI HAR Dataset" --realtime --speed 1 \
  --ground-truth-file data/metrics/ground-truth.jsonl
```

Useful controls are `--loop`, `--scenario 'uci-test-subject-02-*'`, `--device-id`, and
`--no-realtime`. WISDM/SisFall input is strict by default; `--skip-malformed` rejects bad rows and
continues. `ReplayRunner` provides programmatic start, pause, resume, and stop controls.

All loaders emit the sensor service's default units. UCI HAR acceleration is already `g`; WISDM
acceleration is converted from `m/s²` to `g`; SisFall ADXL345 counts are divided by 256 to produce
`g`, and ITG3200 counts are converted to `rad/s`. Overlapped source windows publish one full warm-up
window followed by stride-only chunks so the downstream sliding window does not duplicate samples.

Downloaded datasets must be stored under `data/` and are intentionally excluded from version control.
