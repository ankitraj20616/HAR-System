import unittest

from pydantic import ValidationError

from shared.schemas import (
    Feedback,
    FusedActivity,
    HAREvent,
    SensorPrediction,
    SensorRaw,
    VideoPrediction,
    WebSocketEnvelope,
)

UTC = "2026-06-20T10:00:00.000Z"


class ValidContractExamples(unittest.TestCase):
    def test_all_tdd_examples_validate(self):
        raw = SensorRaw(
            ts=UTC,
            device_id="sim-01",
            sampling_hz=50,
            window={
                "accel": [[0.1, 0.2, 9.8], [0.2, 0.3, 9.7]],
                "gyro": [[0.01, 0.02, 0.03], [0.02, 0.03, 0.04]],
            },
        )
        sensor = SensorPrediction(
            ts=UTC,
            modality="sensor",
            label="WALKING",
            confidence=0.88,
            motion_intensity=0.31,
        )
        video = VideoPrediction(
            ts=UTC,
            modality="video",
            label="LYING",
            confidence=0.82,
            orientation="horizontal",
        )
        fused = FusedActivity(
            ts=UTC,
            activity="WALKING",
            confidence=0.9,
            contributors={"sensor": "WALKING", "video": "WALKING"},
        )
        event = HAREvent(
            ts=UTC,
            type="FALL",
            severity="critical",
            confidence=0.93,
            evidence={"motion_intensity": 0.95, "orientation": "horizontal"},
        )
        feedback = Feedback(
            ts=UTC,
            mode="alert",
            headline="Possible fall detected",
            detail="A sudden movement followed by a lying position was detected.",
            severity="critical",
            recommendations=["Check on the patient immediately."],
            disclaimer="This is an automated assistive tool and not a medical diagnosis.",
        )
        for message in (raw, sensor, video, fused, event, feedback):
            self.assertEqual(message.schema_version, "1.0")

        envelopes = (
            WebSocketEnvelope(channel="activity", data=fused),
            WebSocketEnvelope(channel="event", data=event),
            WebSocketEnvelope(channel="feedback", data=feedback),
        )
        for envelope in envelopes:
            self.assertEqual(envelope.schema_version, "1.0")


class InvalidContractExamples(unittest.TestCase):
    def test_timestamp_must_be_explicit_utc(self):
        base = dict(label="WALKING", confidence=0.8, motion_intensity=0.2)
        for timestamp in (
            "2026-06-20T10:00:00",
            "2026-06-20T15:30:00+05:30",
            1781949600,
            True,
        ):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValidationError):
                SensorPrediction(ts=timestamp, **base)

    def test_confidence_and_labels_are_strict(self):
        for changes in (
            {"confidence": -0.01},
            {"confidence": 1.01},
            {"label": "RUNNING"},
            {"modality": "video"},
            {"schema_version": "2.0"},
        ):
            values = dict(ts=UTC, label="WALKING", confidence=0.8, motion_intensity=0.2)
            values.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                SensorPrediction(**values)

        with self.assertRaises(ValidationError):
            SensorPrediction(
                ts=UTC,
                label="WALKING",
                confidence=0.8,
                motion_intensity=float("nan"),
            )

    def test_sensor_channels_must_be_non_empty_and_aligned(self):
        for window in (
            {"accel": [], "gyro": []},
            {"accel": [[1, 2, 3]], "gyro": [[1, 2, 3], [4, 5, 6]]},
            {"accel": [[1, 2]], "gyro": [[1, 2, 3]]},
        ):
            with self.subTest(window=window), self.assertRaises(ValidationError):
                SensorRaw(ts=UTC, device_id="sim-01", sampling_hz=50, window=window)

    def test_invalid_sensor_window_is_hidden_from_error_text(self):
        sentinel = 123456789.987654321
        with self.assertRaises(ValidationError) as caught:
            SensorRaw(
                ts=UTC,
                device_id="sim-01",
                sampling_hz=50,
                window={"accel": [[sentinel, 2]], "gyro": [[1, 2, 3]]},
            )
        self.assertNotIn(str(sentinel), str(caught.exception))

    def test_extra_fields_and_invalid_severity_are_rejected(self):
        with self.assertRaises(ValidationError):
            HAREvent(
                ts=UTC,
                type="FALL",
                severity="urgent",
                confidence=0.8,
                evidence={},
            )
        with self.assertRaises(ValidationError):
            VideoPrediction(
                ts=UTC,
                label="LYING",
                confidence=0.8,
                orientation="horizontal",
                raw_frame="must never enter the contract",
            )
        with self.assertRaises(ValidationError):
            HAREvent(
                ts=UTC,
                type="FALL",
                severity="critical",
                confidence=0.8,
                evidence={"not_json": object()},
            )

    def test_documented_required_fields_cannot_be_omitted(self):
        required_cases = (
            (
                SensorPrediction,
                dict(ts=UTC, label="WALKING", confidence=0.8, motion_intensity=0.2),
            ),
            (
                VideoPrediction,
                dict(ts=UTC, label="LYING", confidence=0.8, orientation="horizontal"),
            ),
            (
                HAREvent,
                dict(ts=UTC, type="FALL", severity="critical", confidence=0.8),
            ),
            (
                Feedback,
                dict(
                    ts=UTC,
                    mode="feedback",
                    headline="Activity update",
                    detail="A short update.",
                    severity="info",
                    disclaimer="This is not a medical diagnosis.",
                ),
            ),
        )
        for model, values in required_cases:
            with self.subTest(model=model.__name__), self.assertRaises(ValidationError):
                model(**values)

    def test_websocket_channel_and_payload_must_match(self):
        activity = FusedActivity(
            ts=UTC,
            activity="WALKING",
            confidence=0.9,
            contributors={"sensor": "WALKING"},
        )
        with self.assertRaises(ValidationError):
            WebSocketEnvelope(channel="event", data=activity)
        with self.assertRaises(ValidationError):
            WebSocketEnvelope(channel="event", data={"unexpected": "payload"})


if __name__ == "__main__":
    unittest.main()
