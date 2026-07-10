"""Milestone 2 sensor feature, inference, and safety tests."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.sensor_service.classifier import PretrainedModelAdapter
from services.sensor_service.config import SensorSettings
from services.sensor_service.features import extract_features, motion_intensity
from services.sensor_service.local_model import LocalModelError, TFLiteModelRunner
from services.sensor_service.mqtt import SensorMQTTDependency
from services.sensor_service.pipeline import InvalidSensorPayload, SensorPipeline
from services.sensor_service.windowing import (
    GRAVITY_M_S2,
    SensorFrame,
    SensorSample,
    SlidingWindowBuffer,
    StaleSensorPayload,
)
from shared.schemas import SensorRaw
from shared.topics import SENSOR_PREDICTION, SENSOR_RAW

START = datetime(2026, 7, 10, tzinfo=UTC)


def raw_payload(
    count: int,
    *,
    ts: datetime = START,
    accel: tuple[float, float, float] = (0.0, 0.0, 1.0),
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0),
    sampling_hz: float = 50.0,
) -> SensorRaw:
    return SensorRaw(
        ts=ts,
        device_id="test-device",
        sampling_hz=sampling_hz,
        window={"accel": [accel] * count, "gyro": [gyro] * count},
    )


def frame(vectors: list[tuple[float, float, float]]) -> SensorFrame:
    return SensorFrame(
        device_id="test-device",
        sampling_hz=50.0,
        samples=tuple(
            SensorSample(START + timedelta(milliseconds=20 * index), vector, (0.0, 0.0, 0.0))
            for index, vector in enumerate(vectors)
        ),
    )


def test_sensor_config_defaults_and_overlap_validation() -> None:
    settings = SensorSettings()
    assert settings.window_size == 128
    assert settings.window_step == 64
    assert settings.window_overlap == 0.5
    assert settings.sensor_model_revision != "main"

    with pytest.raises(ValidationError):
        SensorSettings(window_size=20, window_overlap=0.99)
    with pytest.raises(ValidationError, match="SENSOR_MODEL_LABELS"):
        SensorSettings(sensor_model_path="model.tflite")


def test_windowing_normalizes_units_and_has_exact_half_overlap() -> None:
    settings = SensorSettings(window_size=20, window_overlap=0.5, accel_unit="g")
    windower = SlidingWindowBuffer(settings)
    frames = windower.add(raw_payload(30))

    assert len(frames) == 2
    assert frames[0].accel[0] == pytest.approx((0.0, 0.0, GRAVITY_M_S2))
    assert frames[0].samples[10:] == frames[1].samples[:10]
    assert frames[0].ts < frames[1].ts


def test_windowing_accepts_full_window_then_stride_chunks_with_end_timestamps() -> None:
    settings = SensorSettings(window_size=20, window_overlap=0.5, accel_unit="g")
    windower = SlidingWindowBuffer(settings)

    first = windower.add(raw_payload(20, ts=START))
    second = windower.add(raw_payload(10, ts=START + timedelta(seconds=0.2)))

    assert len(first) == len(second) == 1
    assert first[0].ts == START
    assert second[0].ts == START + timedelta(seconds=0.2)


def test_windowing_rejects_stale_payloads_and_resets_on_rate_change() -> None:
    windower = SlidingWindowBuffer(SensorSettings(window_size=20))
    assert windower.add(raw_payload(10)) == []
    with pytest.raises(StaleSensorPayload):
        windower.add(raw_payload(10))

    # A changed sampling rate starts a clean buffer for the device.
    changed = raw_payload(20, ts=START + timedelta(seconds=1), sampling_hz=100.0)
    assert len(windower.add(changed)) == 1


def test_raw_contract_rejects_non_finite_and_channel_mismatch() -> None:
    with pytest.raises(ValidationError):
        raw_payload(20, accel=(math.nan, 0.0, 1.0))
    with pytest.raises(ValidationError):
        SensorRaw(
            ts=START,
            device_id="device",
            sampling_hz=50,
            window={"accel": [(0, 0, 1)], "gyro": [(0, 0, 0), (0, 0, 0)]},
        )


def test_feature_formulas_cover_summary_sma_energy_correlations_magnitude_and_tilt() -> None:
    sensor_frame = frame([(1.0, 2.0, 2.0), (3.0, 4.0, 0.0)])
    features = extract_features(sensor_frame)

    assert features["accel_x_mean"] == pytest.approx(2.0)
    assert features["accel_x_std"] == pytest.approx(1.0)
    assert features["accel_x_min"] == 1.0
    assert features["accel_x_max"] == 3.0
    assert features["accel_x_energy"] == pytest.approx(5.0)
    assert features["accel_sma"] == pytest.approx(6.0)
    assert features["accel_corr_xy"] == pytest.approx(1.0)
    assert features["gyro_corr_xy"] == 0.0
    assert features["accel_magnitude_mean"] == pytest.approx(4.0)
    assert features["tilt_x_degrees"] == pytest.approx(
        math.degrees(math.atan2(2.0, math.hypot(3.0, 1.0)))
    )
    assert all(math.isfinite(value) for value in features.values())


def test_motion_intensity_distinguishes_calm_from_spike() -> None:
    calm = frame([(0.0, 0.0, GRAVITY_M_S2)] * 20)
    spike = frame([(0.0, 0.0, GRAVITY_M_S2)] * 19 + [(30.0, 0.0, 0.0)])

    assert motion_intensity(calm) == 0.0
    assert motion_intensity(spike) > 0.9


def test_model_adapter_standardizes_maps_label_and_bounds_confidence() -> None:
    observed = {}

    def runner(accel_window, features):
        observed["window"] = accel_window
        observed["features"] = features
        return {"walk": 1.4, "unmapped-class": 0.2}

    settings = SensorSettings(window_size=20, model_input_mean=0.5, model_input_std=0.5)
    adapter = PretrainedModelAdapter(settings, runner=runner)
    pipeline = SensorPipeline(settings, model=adapter)
    pipeline.start()
    prediction = pipeline.process(raw_payload(20))[0]

    assert prediction.label == "WALKING"
    assert prediction.confidence == 1.0
    assert observed["window"][0] == pytest.approx((-1.0, -1.0, -1.0))
    assert "accel_sma" in observed["features"]


class FakeInterpreter:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.input_tensor = None

    def allocate_tensors(self) -> None:
        pass

    def get_input_details(self):
        import numpy as np

        return [{"shape": [1, 24, 3, 1], "dtype": np.float32, "index": 3}]

    def get_output_details(self):
        return [{"shape": [1, 2], "index": 7}]

    def set_tensor(self, index, tensor) -> None:
        assert index == 3
        self.input_tensor = tensor

    def invoke(self) -> None:
        assert self.input_tensor.shape == (1, 24, 3, 1)

    def get_tensor(self, index):
        import numpy as np

        assert index == 7
        return np.asarray([[1.0, 3.0]], dtype=np.float32)


def test_concrete_local_tflite_runner_resamples_and_softmaxes(tmp_path: Path) -> None:
    model_path = tmp_path / "pinned.tflite"
    model_path.touch()
    runner = TFLiteModelRunner(
        model_path,
        ("SITTING", "WALKING"),
        interpreter_factory=FakeInterpreter,
    )
    scores = runner([(0.0, 0.0, 1.0)] * 20, {})

    assert sum(scores.values()) == pytest.approx(1.0)
    assert scores["WALKING"] > scores["SITTING"]


def test_local_tflite_runner_rejects_missing_artifact() -> None:
    with pytest.raises(LocalModelError, match="does not exist"):
        TFLiteModelRunner(
            Path("/definitely/missing/model.tflite"),
            ("UNKNOWN",),
            interpreter_factory=FakeInterpreter,
        )


def test_configured_missing_local_model_degrades_without_network_access() -> None:
    settings = SensorSettings(
        window_size=20,
        sensor_model_path="/definitely/missing/model.tflite",
        sensor_model_labels="UNKNOWN,WALKING",
        use_fallback=False,
    )
    pipeline = SensorPipeline(settings)
    pipeline.start()
    assert pipeline.health.degraded is True
    assert "local model load failed" in pipeline.health.detail


def test_unmapped_model_label_becomes_unknown() -> None:
    settings = SensorSettings(window_size=20)
    model = PretrainedModelAdapter(settings, runner=lambda *_: ("dancing", 0.91))
    pipeline = SensorPipeline(settings, model=model)
    pipeline.start()

    prediction = pipeline.process(raw_payload(20))[0]
    assert prediction.label == "UNKNOWN"
    assert prediction.confidence == 0.0


def test_missing_model_uses_configured_fallback_and_reports_degraded() -> None:
    fallback_pipeline = SensorPipeline(SensorSettings(window_size=20, use_fallback=True))
    fallback_pipeline.start()
    fallback_prediction = fallback_pipeline.process(raw_payload(20))[0]
    assert fallback_prediction.label == "STANDING"
    assert fallback_prediction.confidence > 0.0
    assert fallback_pipeline.health.degraded is True
    assert "fallback active" in fallback_pipeline.health.detail

    safe_pipeline = SensorPipeline(SensorSettings(window_size=20, use_fallback=False))
    safe_pipeline.start()
    safe_prediction = safe_pipeline.process(raw_payload(20))[0]
    assert safe_prediction.label == "UNKNOWN"
    assert safe_prediction.confidence == 0.0
    assert "UNKNOWN safety mode" in safe_pipeline.health.detail


def test_invalid_json_is_safely_rejected_without_echoing_payload() -> None:
    pipeline = SensorPipeline(SensorSettings(window_size=20))
    secret_payload = '{"bad":"do-not-echo"}'
    with pytest.raises(InvalidSensorPayload) as caught:
        pipeline.process_json(secret_payload)
    assert "do-not-echo" not in str(caught.value)


class FakeMQTTClient:
    def __init__(self) -> None:
        self.subscriptions = []
        self.publications = []

    def subscribe(self, topic, qos):
        self.subscriptions.append((topic, qos))

    def publish(self, topic, payload, qos, retain):
        self.publications.append((topic, json.loads(payload), qos, retain))


def test_mqtt_subscribes_raw_and_publishes_contract_prediction() -> None:
    settings = SensorSettings(window_size=20, use_fallback=True)
    dependency = SensorMQTTDependency(settings)
    dependency.pipeline.start()
    client = FakeMQTTClient()
    dependency._on_connect(client, None, None, 0)  # exercise callback boundary

    message = SimpleNamespace(
        topic=SENSOR_RAW,
        payload=raw_payload(20).model_dump_json().encode(),
    )
    dependency._on_message(client, None, message)

    assert client.subscriptions == [(SENSOR_RAW, 0)]
    assert len(client.publications) == 1
    topic, payload, qos, retained = client.publications[0]
    assert topic == SENSOR_PREDICTION
    assert qos == 1 and retained is False
    assert payload["modality"] == "sensor"
    assert payload["label"] in {
        "WALKING",
        "SITTING",
        "STANDING",
        "LYING",
        "EXERCISING",
        "UNKNOWN",
    }
    assert payload["ts"].endswith("Z")


def test_pipeline_predictions_remain_timestamp_ordered() -> None:
    settings = SensorSettings(window_size=20, window_overlap=0.5, use_fallback=True)
    pipeline = SensorPipeline(settings)
    pipeline.start()
    predictions = pipeline.process(raw_payload(40))
    timestamps = [prediction.ts for prediction in predictions]
    assert timestamps == sorted(timestamps)
    assert len(timestamps) == len(set(timestamps)) == 3
