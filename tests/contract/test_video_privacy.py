"""Static and wire-level audit of the raw-frame privacy boundary."""

from pathlib import Path

from services.video_service.classifier import ActivityClassifier
from services.video_service.config import VideoSettings
from shared.labels import Modality
from shared.schemas import VideoPrediction
from tests.unit.test_video_classifier import standing_pose

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIDEO_SOURCE = PROJECT_ROOT / "services" / "video_service"


def test_video_prediction_wire_payload_contains_no_frame_or_landmarks() -> None:
    result = ActivityClassifier(VideoSettings()).classify(standing_pose())
    prediction = VideoPrediction(
        ts="2026-07-10T00:00:00Z",
        modality=Modality.VIDEO,
        label=result.label,
        confidence=result.confidence,
        orientation=result.orientation,
    )
    payload = prediction.model_dump_json().lower()
    assert "frame" not in payload
    assert "image" not in payload
    assert "landmark" not in payload
    assert "bytes" not in payload


def test_video_service_defines_no_image_encoding_or_persistence_path() -> None:
    source = "\n".join(path.read_text() for path in VIDEO_SOURCE.glob("*.py")).lower()
    forbidden_calls = ("cv2.imwrite", "cv2.imencode", "video writer", "base64.b64encode")
    assert not [call for call in forbidden_calls if call in source]

    generated_media = [
        path
        for path in VIDEO_SOURCE.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".mp4", ".avi"}
    ]
    assert generated_media == []

    database_schema = (PROJECT_ROOT / "shared" / "sql" / "001_init.sql").read_text().lower()
    forbidden_fields = ("bytea", "blob", "raw_frame", "image_data")
    assert not [field for field in forbidden_fields if field in database_schema]
