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

    def _get_detector(self):
        if self._detector is not None:
            return self._detector

        with self._initialization_lock:
            if self._detector is None:
                self._detector = self._detector_factory()

        return self._detector

    def analyze(self, image: np.ndarray) -> list[dict[str, float]]:
        if not self._inference_lock.acquire(blocking=False):
            raise FrameInferenceBusyError(
                "Frame inference is already processing another request."
            )

        try:
            detector = self._get_detector()
            results = detector.detect(image)
            if not results:
                return []

            boxes = getattr(results[0], "boxes", None)
            if boxes is None:
                return []

            coordinates = _as_list(getattr(boxes, "xyxy", []))
            confidences = _as_list(getattr(boxes, "conf", []))
            height, width = image.shape[:2]
            detections = []

            for coordinates_row, confidence in zip(
                coordinates,
                confidences,
            ):
                x1, y1, x2, y2 = (
                    float(value) for value in coordinates_row
                )
                confidence = float(confidence)
                if not all(
                    math.isfinite(value)
                    for value in (x1, y1, x2, y2, confidence)
                ):
                    continue

                x1 = min(max(x1, 0.0), float(width))
                y1 = min(max(y1, 0.0), float(height))
                x2 = min(max(x2, 0.0), float(width))
                y2 = min(max(y2, 0.0), float(height))
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

            return detections
        finally:
            self._inference_lock.release()
