import math
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

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
    pass


class FrameInferenceBusyError(RuntimeError):
    pass


def decode_jpeg(payload: bytes) -> np.ndarray:
    if not payload.startswith(b"\xff\xd8"):
        raise InvalidFrameError("The uploaded frame is not a JPEG image.")

    image = cv2.imdecode(
        np.frombuffer(payload, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None or image.ndim != 3:
        raise InvalidFrameError("The uploaded frame is not a valid JPEG image.")

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
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value


class FrameInferenceService:
    def __init__(
        self,
        detector_factory: Callable[[], Any] = _load_person_detector,
    ):
        self._detector_factory = detector_factory
        self._detector: Any | None = None
        self._initialization_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._face_cascade = None
        self._trackers: dict[str, IoUTrackManager] = {}

    def _get_face_cascade(self):
        if self._face_cascade is None:
            cascade = cv2.CascadeClassifier(str(FACE_CASCADE_PATH))
            if cascade.empty():
                raise RuntimeError("OpenCV face cascade could not be loaded")
            self._face_cascade = cascade
        return self._face_cascade

    def clear_session(self, session_id: str) -> None:
        with self._inference_lock:
            self._trackers.pop(session_id, None)

    def _detect_faces(self, image: np.ndarray) -> list[dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        boxes = self._get_face_cascade().detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32)
        )
        height, width = image.shape[:2]
        return [
            {
                "x1": int(x),
                "y1": int(y),
                "x2": int(min(x + w, width)),
                "y2": int(min(y + h, height)),
                "confidence": None,
                "quality": "detected_unscored",
            }
            for x, y, w, h in boxes
        ]

    def _get_detector(self):
        if self._detector is not None:
            return self._detector

        with self._initialization_lock:
            if self._detector is None:
                self._detector = self._detector_factory()

        return self._detector

    def analyze(self, image: np.ndarray, session_id: str = "default") -> dict[str, Any]:
        if not self._inference_lock.acquire(blocking=False):
            raise FrameInferenceBusyError(
                "Frame inference is already processing another request."
            )

        try:
            detector = self._get_detector()
            results = detector.detect(image)
            if not results:
                detections = []
            else:
                boxes = getattr(results[0], "boxes", None)
                detections = []
                if boxes is not None:
                    coordinates = _as_list(getattr(boxes, "xyxy", []))
                    confidences = _as_list(getattr(boxes, "conf", []))
                    height, width = image.shape[:2]
                    for coordinates_row, confidence in zip(coordinates, confidences):
                        x1, y1, x2, y2 = (float(value) for value in coordinates_row)
                        confidence = float(confidence)
                        if not all(
                            math.isfinite(value)
                            for value in (x1, y1, x2, y2, confidence)
                        ):
                            continue
                        x1, x2 = min(max(x1, 0.0), float(width)), min(
                            max(x2, 0.0), float(width)
                        )
                        y1, y2 = min(max(y1, 0.0), float(height)), min(
                            max(y2, 0.0), float(height)
                        )
                        if x2 <= x1 or y2 <= y1 or not 0.0 <= confidence <= 1.0:
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
            manager = self._trackers.setdefault(session_id, IoUTrackManager())
            detections = manager.update(detections)
            try:
                faces = self._detect_faces(image)
                face_error = None
            except Exception as error:
                faces, face_error = [], str(error)
            return {"detections": detections, "faces": faces, "face_error": face_error}
        finally:
            self._inference_lock.release()


class IoUTrackManager:
    """Greedy IoU tracker with short occlusion tolerance and monotonic IDs."""

    def __init__(self, max_missed: int = 2, min_iou: float = 0.15):
        self.max_missed, self.min_iou = max_missed, min_iou
        self.next_id = 1
        self.tracks: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _iou(a, b):
        x1, y1 = max(a["x1"], b["x1"]), max(a["y1"], b["y1"])
        x2, y2 = min(a["x2"], b["x2"]), min(a["y2"], b["y2"])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
        area_b = (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])
        return intersection / max(area_a + area_b - intersection, 1e-9)

    def update(self, detections):
        pairs = sorted(
            (
                (self._iou(t["box"], d), track_id, index)
                for track_id, t in self.tracks.items()
                for index, d in enumerate(detections)
            ),
            reverse=True,
        )
        matched_tracks, matched_dets = set(), set()
        for score, track_id, index in pairs:
            if (
                score < self.min_iou
                or track_id in matched_tracks
                or index in matched_dets
            ):
                continue
            detections[index]["track_id"] = track_id
            self.tracks[track_id] = {"box": detections[index], "missed": 0}
            matched_tracks.add(track_id)
            matched_dets.add(index)
        for index, detection in enumerate(detections):
            if index in matched_dets:
                continue
            track_id = self.next_id
            self.next_id += 1
            detection["track_id"] = track_id
            self.tracks[track_id] = {"box": detection, "missed": 0}
            matched_tracks.add(track_id)
        for track_id in list(self.tracks):
            if track_id not in matched_tracks:
                self.tracks[track_id]["missed"] += 1
                if self.tracks[track_id]["missed"] > self.max_missed:
                    del self.tracks[track_id]
        return detections
