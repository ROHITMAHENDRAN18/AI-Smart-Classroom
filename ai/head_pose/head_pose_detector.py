"""Standalone head-pose detector based on the current InsightFace landmark layout.

This module intentionally mirrors the live `face.kps` geometry used by the
existing attention estimator in `ai/face_recognition/face_track_association.py`.
It is designed to be independently testable before any live integration.
"""

from __future__ import annotations

import math
import numpy as np


# Calibration mapping from image-coordinate nose offset to pose direction.
# -1 reverses the default image-coordinate convention (positive offset -> RIGHT).
HORIZONTAL_DIRECTION_SIGN = -1.0


def calculate_yaw_ratio(landmarks):
    """Compute the normalized horizontal head-turn ratio from 5 landmarks."""
    if landmarks is None:
        raise ValueError("Facial landmarks cannot be None.")

    points = np.asarray(landmarks, dtype=np.float32)

    if points.ndim != 2 or points.shape[0] < 5 or points.shape[1] < 2:
        raise ValueError("At least 5 2D facial landmarks are required.")

    if not np.isfinite(points[:5]).all():
        raise ValueError("Facial landmarks must contain finite values.")

    left_eye, right_eye, nose, _, _ = points[:5]
    eye_center = (left_eye + right_eye) / 2.0
    eye_distance = float(np.linalg.norm(left_eye - right_eye))

    if eye_distance <= 1e-8:
        return 0.0

    horizontal_offset = abs(float(nose[0] - eye_center[0]))
    return horizontal_offset / eye_distance


def calculate_pitch_ratio(landmarks):
    """Compute the normalized vertical head-tilt ratio from 5 landmarks."""
    if landmarks is None:
        raise ValueError("Facial landmarks cannot be None.")

    points = np.asarray(landmarks, dtype=np.float32)

    if points.ndim != 2 or points.shape[0] < 5 or points.shape[1] < 2:
        raise ValueError("At least 5 2D facial landmarks are required.")

    if not np.isfinite(points[:5]).all():
        raise ValueError("Facial landmarks must contain finite values.")

    left_eye, right_eye, nose, left_mouth, right_mouth = points[:5]
    eye_center = (left_eye + right_eye) / 2.0
    mouth_center = (left_mouth + right_mouth) / 2.0
    face_vertical_distance = float(np.linalg.norm(eye_center - mouth_center))

    if face_vertical_distance <= 1e-8:
        return 0.0

    vertical_offset = float(nose[1] - eye_center[1])
    return vertical_offset / face_vertical_distance


def classify_head_pose(
    yaw_ratio,
    pitch_ratio,
    horizontal_offset=0.0,
    vertical_offset=None,
    max_yaw_ratio=0.22,
    min_pitch_ratio=0.20,
    max_pitch_ratio=0.68,
):
    """Classify the head pose using normalized yaw and pitch ratios.

    A face is classified as FRONT when:
      - yaw_ratio <= max_yaw_ratio (0.22)
      - min_pitch_ratio (0.20) <= pitch_ratio <= max_pitch_ratio (0.68)

    Outside frontal boundaries:
      - pitch_ratio < min_pitch_ratio (nose displaced up towards eyes): UP
      - pitch_ratio > max_pitch_ratio (nose displaced down towards mouth): DOWN
      - horizontal_offset < -max_yaw_ratio (turned to viewer left): LEFT
      - horizontal_offset > max_yaw_ratio (turned to viewer right): RIGHT

    Invalid, non-finite, degenerate, or ambiguous geometries return UNKNOWN.
    There is no unconditional fallback to FRONT.
    """
    try:
        yaw = float(yaw_ratio)
        pitch = float(pitch_ratio if vertical_offset is None else vertical_offset)
        h_off = float(horizontal_offset)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if not (math.isfinite(yaw) and math.isfinite(pitch) and math.isfinite(h_off)):
        return "UNKNOWN"

    if yaw < 0.0:
        return "UNKNOWN"

    # Frontal check
    if yaw <= max_yaw_ratio and (min_pitch_ratio <= pitch <= max_pitch_ratio):
        return "FRONT"

    # Deviations from frontal region
    h_dev = max(0.0, yaw - max_yaw_ratio)

    if pitch < min_pitch_ratio:
        v_dev = min_pitch_ratio - pitch
        v_dir = "UP"
    elif pitch > max_pitch_ratio:
        v_dev = pitch - max_pitch_ratio
        v_dir = "DOWN"
    else:
        v_dev = 0.0
        v_dir = None

    if h_dev > 0.0 and v_dev == 0.0:
        return "LEFT" if h_off < 0.0 else "RIGHT"

    if v_dev > 0.0 and h_dev == 0.0:
        return v_dir

    if h_dev > 0.0 and v_dev > 0.0:
        # Both pitch and yaw deviated from frontal window.
        # Classify by dominant deviation direction.
        if abs(h_dev - v_dev) < 0.02:
            return "LEFT" if h_off < 0.0 else "RIGHT"
        elif h_dev > v_dev:
            return "LEFT" if h_off < 0.0 else "RIGHT"
        else:
            return v_dir

    return "UNKNOWN"


def calculate_head_pose(landmarks):
    """Return yaw, pitch, and pose classification for a face landmark set."""
    if landmarks is None:
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "head_pose": "UNKNOWN",
            "yaw_ratio": 0.0,
            "pitch_ratio": 0.0,
        }

    try:
        points = np.asarray(landmarks, dtype=np.float32)
    except (TypeError, ValueError):
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "head_pose": "UNKNOWN",
            "yaw_ratio": 0.0,
            "pitch_ratio": 0.0,
        }

    if points.ndim != 2 or points.shape[0] < 5 or points.shape[1] < 2:
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "head_pose": "UNKNOWN",
            "yaw_ratio": 0.0,
            "pitch_ratio": 0.0,
        }

    if not np.isfinite(points[:5]).all():
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "head_pose": "UNKNOWN",
            "yaw_ratio": 0.0,
            "pitch_ratio": 0.0,
        }

    left_eye, right_eye, nose, left_mouth, right_mouth = points[:5]
    eye_center = (left_eye + right_eye) / 2.0
    mouth_center = (left_mouth + right_mouth) / 2.0
    eye_distance = float(np.linalg.norm(left_eye - right_eye))
    face_vertical_distance = float(np.linalg.norm(eye_center - mouth_center))

    if eye_distance <= 1e-8 or face_vertical_distance <= 1e-8:
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "head_pose": "UNKNOWN",
            "yaw_ratio": 0.0,
            "pitch_ratio": 0.0,
        }

    horizontal_offset = (
        float(nose[0] - eye_center[0])
        / eye_distance
        * HORIZONTAL_DIRECTION_SIGN
    )
    vertical_offset = float(nose[1] - eye_center[1]) / face_vertical_distance
    yaw_ratio = abs(horizontal_offset)
    pitch_ratio = vertical_offset

    head_pose = classify_head_pose(
        yaw_ratio=yaw_ratio,
        pitch_ratio=pitch_ratio,
        horizontal_offset=horizontal_offset,
        vertical_offset=vertical_offset,
    )

    return {
        "yaw": round(float(yaw_ratio), 4),
        "pitch": round(float(pitch_ratio), 4),
        "head_pose": head_pose,
        "yaw_ratio": round(float(yaw_ratio), 4),
        "pitch_ratio": round(float(pitch_ratio), 4),
    }


def detect_head_pose(landmarks):
    """Alias for `calculate_head_pose` to keep the API consistent across modules."""
    return calculate_head_pose(landmarks)
