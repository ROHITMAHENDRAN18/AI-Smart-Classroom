import math
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.services.face_recognition_service import face_recognition_service
from backend.utils.logger import logger
from configs.settings import (
    FRAME_MAX_HEIGHT,
    FRAME_MAX_PIXELS,
    FRAME_MAX_WIDTH,
    YOLO_MODEL,
)

FACE_CASCADE_PATH = (
    Path(__file__).resolve().parents[2]
    / "models/haarcascade/haarcascade_frontalface_default.xml"
)


class InvalidFrameError(ValueError):
    """Raised when an uploaded frame is not a supported JPEG image."""


class FrameInferenceBusyError(RuntimeError):
    """Raised when another frame is already being processed."""


def decode_jpeg(payload: bytes) -> np.ndarray:
    """Decode and validate an uploaded JPEG frame."""

    if not payload.startswith(b"\xff\xd8"):
        raise InvalidFrameError("The uploaded frame is not a JPEG image.")

    image = cv2.imdecode(
        np.frombuffer(payload, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None or image.ndim != 3:
        raise InvalidFrameError(
            "The uploaded frame is not a valid JPEG image."
        )

    height, width = image.shape[:2]

    if (
        width < 1
        or height < 1
        or width > FRAME_MAX_WIDTH
        or height > FRAME_MAX_HEIGHT
        or width * height > FRAME_MAX_PIXELS
    ):
        raise InvalidFrameError(
            "The uploaded frame dimensions exceed the supported limits."
        )

    return image


def _load_person_detector():
    """Load the configured YOLO person detector."""

    model_path = Path(YOLO_MODEL).expanduser()

    if not model_path.is_absolute():
        model_path = Path.cwd() / model_path

    if not model_path.is_file():
        raise FileNotFoundError(
            "Configured YOLO person-detection weights are unavailable."
        )

    from ai.person_detection.person_detector import PersonDetector

    return PersonDetector(model_path=str(model_path))


def _as_list(value: Any) -> list[Any]:
    """Convert tensors or array-like values into Python lists."""

    if hasattr(value, "cpu"):
        value = value.cpu()

    if hasattr(value, "tolist"):
        value = value.tolist()

    return value


class FrameInferenceService:
    """Run person detection, tracking, and face recognition on a frame."""

    def __init__(
        self,
        detector_factory: Callable[[], Any] = _load_person_detector,
        recognition_service=None,
    ):
        self._detector_factory = detector_factory
        self._recognition_service = (
            recognition_service
            if recognition_service is not None
            else face_recognition_service
        )

        self._detector: Any | None = None
        self._initialization_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._face_cascade = None
        self._trackers: dict[str, "IoUTrackManager"] = {}

    def _get_detector(self):
        """Initialize the person detector once, when first needed."""

        if self._detector is not None:
            return self._detector

        with self._initialization_lock:
            if self._detector is None:
                self._detector = self._detector_factory()

        return self._detector

    def _get_face_cascade(self):
        """Load the Haar cascade used as a face-detection fallback."""

        if self._face_cascade is None:
            if not hasattr(cv2, "CascadeClassifier"):
                raise RuntimeError(
                    "The installed OpenCV build does not include the Haar "
                    "cascade API. Install the project dependencies."
                )

            cascade_path = (
                FACE_CASCADE_PATH
                if (
                    FACE_CASCADE_PATH.is_file()
                    and FACE_CASCADE_PATH.stat().st_size > 0
                )
                else Path(cv2.data.haarcascades)
                / "haarcascade_frontalface_default.xml"
            )

            if (
                not cascade_path.is_file()
                or cascade_path.stat().st_size == 0
            ):
                raise FileNotFoundError(
                    "No usable frontal-face Haar cascade was found."
                )

            cascade = cv2.CascadeClassifier(str(cascade_path))

            if cascade.empty():
                raise RuntimeError(
                    "OpenCV could not load the frontal-face cascade."
                )

            self._face_cascade = cascade

        return self._face_cascade

    def clear_session(self, session_id: str) -> None:
        """Clear temporary tracking state for a session."""

        with self._inference_lock:
            self._trackers.pop(session_id, None)

    def _detect_faces(self, image: np.ndarray) -> list[dict[str, Any]]:
        """Detect faces using Haar when recognition is unavailable."""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        boxes = self._get_face_cascade().detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(32, 32),
        )

        height, width = image.shape[:2]
        faces = []

        for x, y, box_width, box_height in boxes:
            x1 = max(0, int(x))
            y1 = max(0, int(y))
            x2 = min(int(x + box_width), width)
            y2 = min(int(y + box_height), height)

            if x2 <= x1 or y2 <= y1:
                continue

            # Keep this fallback response compatible with existing tests.
            # Recognition metadata is added by analyze() when appropriate.
            faces.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": None,
                    "quality": "detected_unscored",
                }
            )

        return faces

    @staticmethod
    def _sanitize_recognized_faces(
        faces: list[dict[str, Any]],
        image: np.ndarray,
    ) -> list[dict[str, Any]]:
        """Validate face boxes and normalize recognition output."""

        height, width = image.shape[:2]
        sanitized_faces = []

        allowed_quality = {
            "detected_unscored",
            "embedding_available",
            "embedding_unavailable",
        }

        for face in faces:
            try:
                x1 = float(face["x1"])
                y1 = float(face["y1"])
                x2 = float(face["x2"])
                y2 = float(face["y2"])
            except (KeyError, TypeError, ValueError):
                continue

            if not all(
                math.isfinite(value)
                for value in (x1, y1, x2, y2)
            ):
                continue

            x1 = max(0, min(int(x1), width))
            y1 = max(0, min(int(y1), height))
            x2 = max(0, min(int(x2), width))
            y2 = max(0, min(int(y2), height))

            if x2 <= x1 or y2 <= y1:
                continue

            quality = face.get("quality", "detected_unscored")

            if quality not in allowed_quality:
                quality = "detected_unscored"

            raw_student_id = face.get("student_id")
            student_id = (
                str(raw_student_id).strip()
                if raw_student_id is not None
                else None
            )

            if not student_id:
                student_id = None

            identity = face.get("identity", "Unknown")

            if not isinstance(identity, str) or not identity.strip():
                identity = "Unknown"

            if student_id is None:
                identity = "Unknown"

            similarity = face.get("similarity")

            try:
                similarity = (
                    float(similarity)
                    if similarity is not None
                    else None
                )
            except (TypeError, ValueError):
                similarity = None

            if similarity is not None and (
                not math.isfinite(similarity)
                or similarity < -1.0
                or similarity > 1.0
            ):
                similarity = None

            confidence = face.get("confidence")

            try:
                confidence = (
                    float(confidence)
                    if confidence is not None
                    else None
                )
            except (TypeError, ValueError):
                confidence = None

            if confidence is not None and (
                not math.isfinite(confidence)
                or confidence < 0.0
                or confidence > 1.0
            ):
                confidence = None

            sanitized_faces.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": confidence,
                    "quality": quality,
                    "student_id": student_id,
                    "identity": identity,
                    "similarity": similarity,
                    "recognition_status": (
                        "recognized"
                        if student_id is not None
                        else "unknown"
                    ),
                }
            )

        return sanitized_faces

    def analyze(
        self,
        image: np.ndarray,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Analyze one frame and return detections and recognition status."""

        if not self._inference_lock.acquire(blocking=False):
            raise FrameInferenceBusyError(
                "Frame inference is already processing another request."
            )

        try:
            # 1. Person detection
            detector = self._get_detector()
            results = detector.detect(image)
            detections = []

            if results:
                boxes = getattr(results[0], "boxes", None)

                if boxes is not None:
                    coordinates = _as_list(
                        getattr(boxes, "xyxy", [])
                    )
                    confidences = _as_list(
                        getattr(boxes, "conf", [])
                    )

                    height, width = image.shape[:2]

                    for coordinates_row, raw_confidence in zip(
                        coordinates,
                        confidences,
                    ):
                        try:
                            if len(coordinates_row) < 4:
                                continue

                            x1, y1, x2, y2 = (
                                float(value)
                                for value in coordinates_row[:4]
                            )
                            confidence = float(raw_confidence)

                        except (TypeError, ValueError):
                            continue

                        if not all(
                            math.isfinite(value)
                            for value in (
                                x1,
                                y1,
                                x2,
                                y2,
                                confidence,
                            )
                        ):
                            continue

                        x1 = min(max(x1, 0.0), float(width))
                        x2 = min(max(x2, 0.0), float(width))
                        y1 = min(max(y1, 0.0), float(height))
                        y2 = min(max(y2, 0.0), float(height))

                        if (
                            x2 <= x1
                            or y2 <= y1
                            or not 0.0 <= confidence <= 1.0
                        ):
                            continue

                        detections.append(
                            {
                                "class_label": "person",
                                "x1": x1,
                                "y1": y1,
                                "x2": x2,
                                "y2": y2,
                                "confidence": confidence,
                            }
                        )

            # 2. Session-scoped tracking.
            # Track IDs are temporary and are never used as student IDs.
            manager = self._trackers.setdefault(
                session_id,
                IoUTrackManager(),
            )
            detections = manager.update(detections)

            # 3. Face recognition, with Haar fallback if recognition fails.
            recognition_attempted = True
            recognition_error = None
            face_error = None

            try:
                recognized_faces = self._recognition_service.analyze(image)

                faces = self._sanitize_recognized_faces(
                    recognized_faces,
                    image,
                )

            except Exception as error:
                recognition_error = (
                    f"{type(error).__name__}: {error}"
                )

                logger.exception(
                    "face_recognition_failed session_id=%s",
                    session_id,
                )

                try:
                    fallback_faces = self._detect_faces(image)

                    faces = self._sanitize_recognized_faces(
                        fallback_faces,
                        image,
                    )

                    # Haar detects faces but cannot establish identity.
                    for face in faces:
                        face["student_id"] = None
                        face["identity"] = "Unknown"
                        face["similarity"] = None
                        face["recognition_status"] = "unavailable"

                except Exception as fallback_error:
                    logger.exception(
                        "face_detection_failed session_id=%s "
                        "image_width=%s image_height=%s",
                        session_id,
                        image.shape[1] if image.ndim >= 2 else None,
                        image.shape[0] if image.ndim >= 2 else None,
                    )

                    faces = []
                    face_error = (
                        f"{type(fallback_error).__name__}: "
                        f"{fallback_error}"
                    )

            return {
                "detections": detections,
                "faces": faces,
                "face_error": face_error,
                "recognition_error": recognition_error,
                "recognition_attempted": recognition_attempted,
            }

        finally:
            self._inference_lock.release()


class IoUTrackManager:
    """Greedy IoU tracker with short occlusion tolerance and monotonic IDs."""

    def __init__(
        self,
        max_missed: int = 2,
        min_iou: float = 0.15,
    ):
        self.max_missed = max_missed
        self.min_iou = min_iou
        self.next_id = 1
        self.tracks: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _iou(a, b):
        x1 = max(a["x1"], b["x1"])
        y1 = max(a["y1"], b["y1"])
        x2 = min(a["x2"], b["x2"])
        y2 = min(a["y2"], b["y2"])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        area_a = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
        area_b = (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])

        union = area_a + area_b - intersection

        return intersection / max(union, 1e-9)

    def update(self, detections):
        """Assign temporary tracking IDs to person detections."""

        pairs = sorted(
            (
                (self._iou(track["box"], detection), track_id, index)
                for track_id, track in self.tracks.items()
                for index, detection in enumerate(detections)
            ),
            reverse=True,
        )

        matched_tracks = set()
        matched_detections = set()

        for score, track_id, index in pairs:
            if (
                score < self.min_iou
                or track_id in matched_tracks
                or index in matched_detections
            ):
                continue

            detections[index]["track_id"] = track_id

            self.tracks[track_id] = {
                "box": detections[index].copy(),
                "missed": 0,
            }

            matched_tracks.add(track_id)
            matched_detections.add(index)

        for index, detection in enumerate(detections):
            if index in matched_detections:
                continue

            track_id = self.next_id
            self.next_id += 1

            detection["track_id"] = track_id

            self.tracks[track_id] = {
                "box": detection.copy(),
                "missed": 0,
            }

            matched_tracks.add(track_id)

        for track_id in list(self.tracks):
            if track_id not in matched_tracks:
                self.tracks[track_id]["missed"] += 1

                if (
                    self.tracks[track_id]["missed"]
                    > self.max_missed
                ):
                    del self.tracks[track_id]

        return detections