import os
import pickle
import tempfile
import threading
from pathlib import Path
from typing import Any

import numpy as np

from configs.settings import FACE_RECOGNITION_THRESHOLD
from backend.utils.logger import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDINGS_PATH = PROJECT_ROOT / "embeddings" / "face_embeddings.pkl"
EMBEDDING_DIMENSIONS = 512


def normalize_embedding(value: Any) -> np.ndarray | None:
    try:
        vector = np.asarray(value, dtype=np.float32).reshape(-1)
    except (TypeError, ValueError):
        return None

    if (
        vector.size != EMBEDDING_DIMENSIONS
        or not np.isfinite(vector).all()
    ):
        return None

    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        return None

    return vector / norm


class FaceRecognitionService:
    """InsightFace inference and atomic persistence of student embeddings."""

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
        self._enrollment_lock = threading.Lock()
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

    def _read_raw_embeddings(self) -> dict:
        if not self._embeddings_path.is_file():
            return {}

        with self._embeddings_path.open("rb") as file:
            data = pickle.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Face embeddings must contain a student-ID mapping."
            )

        return data

    @staticmethod
    def _normalize_mapping(raw_embeddings: dict) -> dict[str, np.ndarray]:
        normalized: dict[str, np.ndarray] = {}

        for student_id, values in raw_embeddings.items():
            if not isinstance(values, (list, tuple, np.ndarray)):
                continue

            if isinstance(values, np.ndarray) and values.ndim == 1:
                values = [values]

            vectors = []
            for value in values:
                vector = normalize_embedding(value)
                if vector is not None:
                    vectors.append(vector)

            if vectors:
                normalized[str(student_id)] = np.stack(vectors)

        return normalized

    def _ensure_model(self) -> None:
        if self._model is not None:
            return

        with self._initialization_lock:
            if self._model is not None:
                return

            try:
                self._model = self._model_factory()
                logger.info("face_recognition_model_initialized")
            except Exception as error:
                logger.exception("face_recognition_model_initialization_failed")
                raise RuntimeError(
                    "Face recognition model could not be initialized."
                ) from error

    def _refresh_embeddings(self, *, allow_empty: bool = False) -> None:
        raw_embeddings = self._read_raw_embeddings()
        normalized = self._normalize_mapping(raw_embeddings)

        if not normalized and not allow_empty:
            raise RuntimeError(
                "No valid 512-dimensional student embeddings are available."
            )

        # Assign a complete mapping at once so inference doesn't see a partial update.
        self._embeddings = normalized
        self._load_error = None

    def _atomic_write_embeddings(self, raw_embeddings: dict) -> None:
        target = self._embeddings_path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                pickle.dump(raw_embeddings, file, protocol=pickle.HIGHEST_PROTOCOL)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, target)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def enroll(self, student_id: str, image: np.ndarray) -> dict[str, Any]:
        """Generate and persist an embedding from an image containing one face."""
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("A valid decoded image is required.")

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("The image must be a three-channel color image.")

        self._ensure_model()

        # Serialize enrollment writes and face-model inference.
        with self._enrollment_lock:
            with self._inference_lock:
                faces = self._model.get(image)

            if len(faces) != 1:
                raise ValueError(
                    "Enrollment image must contain exactly one detectable face."
                )

            face = faces[0]
            embedding = normalize_embedding(
                getattr(face, "normed_embedding", None)
            )

            if embedding is None:
                embedding = normalize_embedding(
                    getattr(face, "embedding", None)
                )

            if embedding is None:
                raise ValueError(
                    "A valid 512-dimensional face embedding could not be generated."
                )

            raw_embeddings = self._read_raw_embeddings()
            existing = raw_embeddings.get(student_id, [])

            if isinstance(existing, np.ndarray):
                existing = [existing] if existing.ndim == 1 else list(existing)
            elif not isinstance(existing, (list, tuple)):
                existing = []

            updated = dict(raw_embeddings)
            updated[student_id] = [*existing, embedding.copy()]

            # Persist before reporting success to the API.
            self._atomic_write_embeddings(updated)

            # Refresh the recognition cache after the successful file replacement.
            self._embeddings = self._normalize_mapping(updated)
            self._load_error = None

            logger.info(
                "face_enrollment_saved student_id=%s total_embeddings=%s",
                student_id,
                len(updated[student_id]),
            )

        return {
            "student_id": student_id,
            "embedding_dimensions": int(embedding.size),
        }

    def analyze(self, image: np.ndarray) -> list[dict[str, Any]]:
        """Detect faces and return identity matches; unmatched faces remain Unknown."""
        self._ensure_model()

        if not self._embeddings:
            try:
                self._refresh_embeddings()
            except Exception as error:
                logger.exception("face_embeddings_load_failed")
                raise RuntimeError(
                    "Face recognition embeddings are unavailable."
                ) from error

        with self._inference_lock:
            faces = self._model.get(image)

        height, width = image.shape[:2]
        output = []
        embeddings = self._embeddings

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

                for candidate_id, vectors in embeddings.items():
                    if vectors.shape[1] != query.size:
                        continue

                    score = float(np.max(vectors @ query))
                    if score > best_score:
                        best_id = candidate_id
                        best_score = score

                if best_id is not None:
                    similarity = max(-1.0, min(1.0, best_score))
                    if similarity >= self._threshold:
                        student_id = best_id

            landmarks = getattr(face, "kps", None)

            output.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": None,
                    "quality": (
                        "embedding_available"
                        if query is not None
                        else "embedding_unavailable"
                    ),
                    "student_id": student_id,
                    "identity": student_id if student_id else "Unknown",
                    "landmarks": (
                        np.asarray(landmarks, dtype=np.float32).tolist()
                        if landmarks is not None
                        else None
                    ),
                    "similarity": similarity,
                }
            )

        return output


face_recognition_service = FaceRecognitionService()