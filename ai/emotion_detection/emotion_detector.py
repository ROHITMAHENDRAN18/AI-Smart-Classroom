"""Standalone emotion detector based on facial landmark geometry.

This module intentionally does not alter the live classroom attention pipeline.
It provides an isolated, independently testable emotion signal based on face
landmarks already available in the project stack.
"""

from __future__ import annotations

import numpy as np


SUPPORTED_EMOTIONS = ["HAPPY", "SAD", "ANGRY", "SURPRISED", "NEUTRAL"]


def mouth_openness_ratio(landmarks):
    """Heuristic: open mouth = large distance between lips compared to face width."""
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 18:
        raise ValueError("At least 18 facial landmarks are required for emotion classification.")

    left_corner = points[15]
    right_corner = points[17]
    mouth_center = points[16]

    mouth_width = np.linalg.norm(right_corner - left_corner)
    mouth_height = abs(mouth_center[1] - ((left_corner[1] + right_corner[1]) / 2.0))

    if mouth_width <= 1e-8:
        return 0.0

    return mouth_height / mouth_width


def brow_tension_ratio(landmarks):
    """Heuristic: flattened brows produce a calm-neutral face; raised brows imply surprise."""
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 18:
        raise ValueError("At least 18 facial landmarks are required for emotion classification.")

    left_brow = points[5]
    right_brow = points[9]
    eye_center = (points[0] + points[4]) / 2.0

    brow_span = np.linalg.norm(right_brow - left_brow)
    if brow_span <= 1e-8:
        return 0.0

    brow_offset = abs((left_brow[1] + right_brow[1]) / 2.0 - eye_center[1])
    return brow_offset / brow_span


def classify_emotion(landmarks):
    """Classify a face into a coarse emotion using landmark heuristics."""
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 18:
        raise ValueError("At least 18 facial landmarks are required for emotion classification.")

    openness = mouth_openness_ratio(points)
    brow_tension = brow_tension_ratio(points)

    if openness > 0.45:
        return "SURPRISED"

    if openness > 0.12 and brow_tension <= 0.15:
        return "HAPPY"

    if openness < 0.08:
        return "SAD"

    if openness > 0.12 and brow_tension > 0.15:
        return "ANGRY"

    return "NEUTRAL"


def estimate_emotion(landmarks):
    """Backward-compatible alias for the emotion classifier."""
    return classify_emotion(landmarks)


def detect_emotion(landmarks):
    """Return a structured emotion result.

    Example return:
    {
        "emotion": "HAPPY",
        "confidence": 0.82,
        "emotion_label": "HAPPY"
    }
    """
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 18:
        raise ValueError("At least 18 facial landmarks are required for emotion classification.")

    emotion = classify_emotion(points)
    openness = mouth_openness_ratio(points)
    brow_tension = brow_tension_ratio(points)

    if emotion == "HAPPY":
        confidence = min(0.95, 0.55 + openness * 1.5)
    elif emotion == "SURPRISED":
        confidence = min(0.96, 0.60 + brow_tension * 2.0)
    elif emotion == "ANGRY":
        confidence = min(0.94, 0.50 + brow_tension * 1.8)
    elif emotion == "SAD":
        confidence = min(0.92, 0.60 + (0.15 - openness) * 2.5)
    else:
        confidence = 0.60

    return {
        "emotion": emotion,
        "confidence": float(np.clip(confidence, 0.0, 1.0)),
        "emotion_label": emotion,
    }
