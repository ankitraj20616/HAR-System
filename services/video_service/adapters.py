"""Optional local camera, pose, and MQTT adapters.

Heavy vision packages are imported lazily so geometry tests and API health can
run on systems without a webcam or MediaPipe installation.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from services.runtime import MQTTDependency
from services.video_service.landmarks import Landmark, PoseLandmarks
from shared.schemas import VideoPrediction
from shared.topics import VIDEO_PREDICTION, policy_for


class OpenCVCamera:
    """Small capture adapter with no recording or image-writing API."""

    def __init__(self, camera_index: int, fps: float) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required for webcam capture") from exc
        self._capture = cv2.VideoCapture(camera_index)
        self._capture.set(cv2.CAP_PROP_FPS, fps)

    @property
    def is_opened(self) -> bool:
        return bool(self._capture.isOpened())

    def read(self) -> tuple[bool, Any]:
        return self._capture.read()

    def release(self) -> None:
        self._capture.release()


class MediaPipePoseEstimator:
    """Convert MediaPipe's result immediately into numeric landmark objects."""

    def __init__(self, min_visibility: float) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("mediapipe is required for local pose estimation") from exc
        self._mp = mp
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=min_visibility,
            min_tracking_confidence=min_visibility,
        )

    def estimate(self, frame: Any) -> PoseLandmarks | None:
        # Conversion is kept here; neither the result object nor the frame is retained.
        cv2 = __import__("cv2")
        result = self._pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if result.pose_landmarks is None:
            return None
        pose_landmark = self._mp.solutions.pose.PoseLandmark
        wanted = {
            "left_shoulder": pose_landmark.LEFT_SHOULDER,
            "right_shoulder": pose_landmark.RIGHT_SHOULDER,
            "left_hip": pose_landmark.LEFT_HIP,
            "right_hip": pose_landmark.RIGHT_HIP,
            "left_knee": pose_landmark.LEFT_KNEE,
            "right_knee": pose_landmark.RIGHT_KNEE,
            "left_ankle": pose_landmark.LEFT_ANKLE,
            "right_ankle": pose_landmark.RIGHT_ANKLE,
            "left_wrist": pose_landmark.LEFT_WRIST,
            "right_wrist": pose_landmark.RIGHT_WRIST,
        }
        return PoseLandmarks(
            {
                name: Landmark(
                    x=result.pose_landmarks.landmark[index].x,
                    y=result.pose_landmarks.landmark[index].y,
                    z=result.pose_landmarks.landmark[index].z,
                    visibility=result.pose_landmarks.landmark[index].visibility,
                )
                for name, index in wanted.items()
            }
        )

    def close(self) -> None:
        with suppress(Exception):
            self._pose.close()


class VideoMQTTPublisher(MQTTDependency):
    """Managed MQTT connection that only accepts the strict video contract."""

    def publish(self, prediction: VideoPrediction) -> None:
        client = self._client
        if client is None:
            raise ConnectionError("MQTT publisher is not started")
        policy = policy_for(VIDEO_PREDICTION)
        result = client.publish(
            policy.topic,
            payload=prediction.model_dump_json(),
            qos=policy.qos,
            retain=policy.retain,
        )
        result_code = getattr(result, "rc", 0)
        if result_code != 0:
            raise ConnectionError(f"MQTT publish failed with code {result_code}")
