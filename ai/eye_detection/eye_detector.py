"""Standalone eye detector supporting eye contour landmarks and MediaPipe FaceMesh.

This module computes Eye Aspect Ratio (EAR) using genuine 6-point eye contour landmarks:
    - left outer corner
    - top eyelid
    - top center
    - right outer corner / inner corner
    - bottom center
    - bottom eyelid

Five-point InsightFace facial keypoints (left eye center, right eye center, nose,
left mouth corner, right mouth corner) do NOT contain eye contour landmarks and
cannot be used for EAR calculation. When only 5 keypoints are available or when
face crops are occluded / too small (<35px), this module safely returns UNKNOWN
with an explicit explanatory reason without crashing or fabricating landmarks.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple
import numpy as np

# Standard MediaPipe FaceMesh landmark indices for 6-point eye contours:
# Left eye: outer corner (33), top outer (160), top inner (158), inner corner (133), bottom inner (153), bottom outer (144)
# Right eye: outer corner (362), top outer (385), top inner (387), inner corner (263), bottom inner (373), bottom outer (380)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

_face_mesh_instance = None


class _InsightFaceMeshAdapter:
    """Robust 6-point eye contour extractor using InsightFace's landmark detector."""

    def __init__(self):
        from insightface.app import FaceAnalysis

        self._app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        self._app.prepare(ctx_id=-1, det_size=(320, 320))

    def extract_eyes(
        self, face_image: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        if face_image is None or not isinstance(face_image, np.ndarray) or face_image.size == 0:
            return None, "Face image is missing or empty."
        faces = self._app.get(face_image)
        if not faces:
            return None, "No face detected in crop."
        l68 = getattr(faces[0], "landmark_3d_68", None)
        if l68 is None or len(l68) < 68:
            return None, "No 68-point landmarks in face."
        eye1 = l68[36:42, :2]
        eye2 = l68[42:48, :2]
        return np.array([eye1, eye2], dtype=np.float32), None


def extract_eye_landmarks_from_68_points(
    landmarks_68: Any,
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Extract left and right 6-point eye contours from standard 68-point facial landmarks.

    In standard 68-point facial landmarks:
        Eye 1: indices 36 to 41
        Eye 2: indices 42 to 47
    """
    if landmarks_68 is None:
        return None, "Landmarks are None."
    try:
        pts = np.asarray(landmarks_68, dtype=np.float32)
    except (TypeError, ValueError):
        return None, "Invalid landmark points array."

    if pts.ndim != 2 or pts.shape[0] < 68 or pts.shape[1] < 2:
        return None, f"Expected at least 68 2D landmark points, got shape {pts.shape}."

    if not np.isfinite(pts[:68, :2]).all():
        return None, "Landmarks contain non-finite values."

    eye1 = pts[36:42, :2]
    eye2 = pts[42:48, :2]
    return np.array([eye1, eye2], dtype=np.float32), None


def get_face_mesh():
    """Lazily initialize MediaPipe FaceMesh or InsightFace adapter for eye contour extraction."""
    global _face_mesh_instance
    if _face_mesh_instance is None:
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            _face_mesh_instance = mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )
        except Exception:
            try:
                _face_mesh_instance = _InsightFaceMeshAdapter()
            except Exception:
                _face_mesh_instance = False
    return _face_mesh_instance if _face_mesh_instance is not False else None


def calculate_eye_aspect_ratio(eye_points):
    """Return the Eye Aspect Ratio (EAR) for a single eye with at least 6 contour points.

    Standard EAR formula (Soukupová & Čech):
        (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
    """
    if eye_points is None:
        raise ValueError("Eye points cannot be None.")

    eye = np.asarray(eye_points, dtype=np.float32)

    if eye.ndim != 2 or eye.shape[0] < 6 or eye.shape[1] < 2:
        raise ValueError(
            f"Eye points must contain at least 6 2D contour points; got shape {eye.shape}."
        )

    if not np.isfinite(eye[:6]).all():
        raise ValueError("Eye contour landmarks must contain finite coordinates.")

    p1, p2, p3, p4, p5, p6 = eye[:6]

    vertical_1 = float(np.linalg.norm(p2 - p6))
    vertical_2 = float(np.linalg.norm(p3 - p5))
    horizontal = float(np.linalg.norm(p1 - p4))

    if horizontal <= 1e-8:
        return 0.0

    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def calculate_left_eye_ear(eye_pair):
    """Calculate the EAR for the left eye from a pair of eyes."""
    if eye_pair is None:
        raise ValueError("Eye pair cannot be None.")

    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must provide both left and right eyes.")

    left_eye = eye_pair[0]
    return calculate_eye_aspect_ratio(left_eye)


def calculate_right_eye_ear(eye_pair):
    """Calculate the EAR for the right eye from a pair of eyes."""
    if eye_pair is None:
        raise ValueError("Eye pair cannot be None.")

    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must provide both left and right eyes.")

    right_eye = eye_pair[1]
    return calculate_eye_aspect_ratio(right_eye)


def calculate_average_ear(eye_pair):
    """Return the average EAR between the left and right eyes."""
    if eye_pair is None:
        raise ValueError("Eye pair cannot be None.")

    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must provide both left and right eyes.")

    left_ear = calculate_left_eye_ear(eye_pair)
    right_ear = calculate_right_eye_ear(eye_pair)
    return (left_ear + right_ear) / 2.0


def classify_eye_state(ear_value, open_threshold=0.22, closed_threshold=0.18):
    """Classify the eye as OPEN, CLOSED, or PARTIAL based on EAR threshold."""
    if ear_value is None:
        return "UNKNOWN"

    try:
        val = float(ear_value)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if not math.isfinite(val) or val < 0.0:
        return "UNKNOWN"

    if val >= open_threshold:
        return "OPEN"

    if val <= closed_threshold:
        return "CLOSED"

    return "PARTIAL"


def detect_eye_state(eye_pair, open_threshold=0.22, closed_threshold=0.18):
    """Return a structured eye-state result from a pair of 6-point eyes.

    Example return:
    {
        "left_ear": 0.31,
        "right_ear": 0.29,
        "average_ear": 0.30,
        "eye_state": "OPEN",
        "reason": None
    }
    """
    if eye_pair is None:
        raise ValueError("Eye pair cannot be None.")

    points = np.asarray(eye_pair, dtype=np.float32)

    # If caller accidentally passes 5-point InsightFace landmarks
    if points.ndim == 2 and points.shape[0] == 5:
        raise ValueError(
            "Five-point facial keypoints do not contain eye contour landmarks. "
            "Use detect_eye_state_from_face(face_crop) to extract contour landmarks via MediaPipe."
        )

    if points.shape[0] < 2:
        raise ValueError("Eye pair must contain left and right eye landmarks.")

    left_ear = calculate_left_eye_ear(points)
    right_ear = calculate_right_eye_ear(points)
    average_ear = calculate_average_ear(points)

    eye_state = classify_eye_state(
        average_ear,
        open_threshold=open_threshold,
        closed_threshold=closed_threshold,
    )

    return {
        "left_ear": round(float(left_ear), 4),
        "right_ear": round(float(right_ear), 4),
        "average_ear": round(float(average_ear), 4),
        "eye_state": eye_state,
        "reason": None,
    }


def extract_eye_landmarks_from_face(
    face_image: np.ndarray,
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Extract 6 left-eye and 6 right-eye contour landmarks from a face crop using MediaPipe.

    Returns:
        (eye_pair_landmarks, reason_if_unavailable)
    """
    if face_image is None or not isinstance(face_image, np.ndarray):
        return None, "Face image is missing or invalid."

    if face_image.size == 0:
        return None, "Face image has zero dimensions."

    height, width = face_image.shape[:2]
    if height < 35 or width < 35:
        return None, f"Face crop too small ({width}x{height}px < 35x35 minimum) for reliable eye contour detection."

    mesh = get_face_mesh()
    if mesh is None:
        return None, "Eye contour detector is unavailable in this environment."

    if isinstance(mesh, _InsightFaceMeshAdapter):
        return mesh.extract_eyes(face_image)

    try:
        import cv2

        if len(face_image.shape) == 2:
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_GRAY2RGB)
        elif face_image.shape[2] == 4:
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGRA2RGB)
        else:
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)

        results = mesh.process(rgb_image)
        if not results or not results.multi_face_landmarks:
            return None, "No facial landmark mesh detected in face crop (possible extreme occlusion or angle)."

        landmarks = results.multi_face_landmarks[0].landmark

        left_pts = np.array(
            [[landmarks[i].x * width, landmarks[i].y * height] for i in LEFT_EYE_INDICES],
            dtype=np.float32,
        )
        right_pts = np.array(
            [[landmarks[i].x * width, landmarks[i].y * height] for i in RIGHT_EYE_INDICES],
            dtype=np.float32,
        )

        return np.array([left_pts, right_pts], dtype=np.float32), None

    except Exception as error:
        return None, f"Eye landmark extraction failed: {error}"


def detect_eye_state_from_face(
    face_image: np.ndarray | None = None,
    open_threshold: float = 0.22,
    closed_threshold: float = 0.18,
    landmarks_68: Any = None,
) -> Dict[str, Any]:
    """Extract eye landmarks from a face crop or 68-point landmarks and classify eye state.

    Safely returns UNKNOWN if landmarks are unavailable without throwing.
    """
    if landmarks_68 is not None:
        landmarks, reason = extract_eye_landmarks_from_68_points(landmarks_68)
    else:
        landmarks, reason = extract_eye_landmarks_from_face(face_image)

    if landmarks is None:
        return {
            "left_ear": None,
            "right_ear": None,
            "average_ear": None,
            "eye_state": "UNKNOWN",
            "reason": reason,
        }

    try:
        result = detect_eye_state(
            landmarks,
            open_threshold=open_threshold,
            closed_threshold=closed_threshold,
        )
        return result
    except Exception as error:
        return {
            "left_ear": None,
            "right_ear": None,
            "average_ear": None,
            "eye_state": "UNKNOWN",
            "reason": f"Eye state classification error: {error}",
        }
