import pickle
import threading
from pathlib import Path
from typing import Any

import numpy as np

from configs.settings import FACE_RECOGNITION_THRESHOLD
from backend.utils.logger import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDINGS_PATH = PROJECT_ROOT / "embeddings" / "face_embeddings.pkl"


def normalize_embedding(value: Any) -> np.ndarray | None:
    try:
        vector = np.asarray(value, dtype=np.float32).reshape(-1)
    except (TypeError, ValueError):
        return None

    if vector.size == 0 or not np.isfinite(vector).all():
        return None

    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        return None

    return vector / norm


class FaceRecognitionService:
    """Lazy InsightFace inference with existing student embeddings."""

    def __init__(
        self,
        model_factory=None,
        embeddings_path: Path = EMBEDDINGS_PATH,
        threshold: float = FACE_RECOGNITION_THRESHOLD,
    ):
        self._model_factory = model_factory or self._create_model
        self._embeddings_path = Path(embeddings_path)
        self._threshold = float(threshold)
        self._model = None
        self._embeddings: dict[str, np.ndarray] = {}
        self._initialization_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._load_error: str | None = None

    @staticmethod
    def _create_model():
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        app.prepare(ctx_id=-1, det_size=(640, 640))
        return app

    def _ensure_initialized(self) -> None:
        if self._model is not None and self._embeddings:
            return

        with self._initialization_lock:
            if self._model is not None and self._embeddings:
                return

            if self._load_error is not None:
                raise RuntimeError(self._load_error)

            try:
                if not self._embeddings_path.is_file():
                    raise FileNotFoundError(
                        f"Face embeddings file not found: {self._embeddings_path}"
                    )

                with self._embeddings_path.open("rb") as file:
                    raw_embeddings = pickle.load(file)

                if not isinstance(raw_embeddings, dict):
                    raise ValueError("Face embeddings must contain a student-ID mapping.")

                normalized_embeddings: dict[str, np.ndarray] = {}

                for student_id, values in raw_embeddings.items():
                    vectors = []
                    for value in values:
                        vector = normalize_embedding(value)
                        if vector is not None and vector.size == 512:
                            vectors.append(vector)

                    if vectors:
                        normalized_embeddings[str(student_id)] = np.stack(vectors)

                if not normalized_embeddings:
                    raise ValueError(
                        "No valid 512-dimensional student embeddings were loaded."
                    )

                self._model = self._model_factory()
                self._embeddings = normalized_embeddings

                logger.info(
                    "face_recognition_initialized students=%s embeddings=%s",
                    len(normalized_embeddings),
                    sum(len(vectors) for vectors in normalized_embeddings.values()),
                )
            except Exception as error:
                self._load_error = (
                    f"Face recognition initialization failed: {type(error).__name__}: "
                    f"{error}"
                )
                logger.exception("face_recognition_initialization_failed")
                raise RuntimeError(self._load_error) from error

    def analyze(self, image: np.ndarray) -> list[dict[str, Any]]:
        """Detect faces and return identity matches; unmatched faces remain Unknown."""
        self._ensure_initialized()

        with self._inference_lock:
            faces = self._model.get(image)

        height, width = image.shape[:2]
        output = []

        for face in faces:
            bbox = np.asarray(face.bbox).reshape(-1)
            if bbox.size < 4 or not np.isfinite(bbox[:4]).all():
                continue

            x1, y1, x2, y2 = bbox[:4]
            x1 = max(0, min(int(x1), width))
            y1 = max(0, min(int(y1), height))
            x2 = max(0, min(int(x2), width))
            y2 = max(0, min(int(y2), height))

            if x2 <= x1 or y2 <= y1:
                continue

            query = normalize_embedding(
                getattr(face, "normed_embedding", None)
            )

            student_id = None
            similarity = None

            if query is not None:
                best_id = None
                best_score = -1.0

                for candidate_id, vectors in self._embeddings.items():
                    if vectors.shape[1] != query.size:
                        continue

                    scores = vectors @ query
                    score = float(np.max(scores))

                    if score > best_score:
                        best_id = candidate_id
                        best_score = score

                if best_id is not None:
                    similarity = max(-1.0, min(1.0, best_score))
                    if similarity >= self._threshold:
                        student_id = best_id

            output.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": None,
                    "quality": "embedding_available" if query is not None else "embedding_unavailable",
                    "student_id": student_id,
                    "identity": student_id if student_id else "Unknown",
                    "similarity": similarity,
                }
            )

        return output


face_recognition_service = FaceRecognitionService()
