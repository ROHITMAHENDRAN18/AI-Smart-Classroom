"""Standalone eye detector using existing InsightFace facial keypoints.

This module does not replace the existing attention or face-recognition flow.
It provides a reusable eye-state calculation using the eye landmark geometry
that is already available via ``face.kps`` from InsightFace.
"""

from __future__ import annotations

import numpy as np


def calculate_eye_aspect_ratio(eye_points):
    """Return the Eye Aspect Ratio (EAR) for a single eye.

    Expected eye_points order is roughly:
    - left outer corner
    - top eyelid
    - top center
    - right outer corner
    - bottom center
    - bottom eyelid

    A standard EAR calculation is:
        (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
    """
    eye = np.asarray(eye_points, dtype=np.float32)

    if eye.shape[0] < 6:
        raise ValueError("Eye points must contain at least 6 landmark points.")

    p1, p2, p3, p4, p5, p6 = eye[:6]

    vertical_1 = np.linalg.norm(p2 - p6)
    vertical_2 = np.linalg.norm(p3 - p5)
    horizontal = np.linalg.norm(p1 - p4)

    if horizontal <= 1e-8:
        return 0.0

    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def calculate_left_eye_ear(eye_pair):
    """Calculate the EAR for the left eye from a pair of eyes."""
    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must provide both left and right eyes.")

    left_eye = eye_pair[0]
    return calculate_eye_aspect_ratio(left_eye)


def calculate_right_eye_ear(eye_pair):
    """Calculate the EAR for the right eye from a pair of eyes."""
    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must provide both left and right eyes.")

    right_eye = eye_pair[1]
    return calculate_eye_aspect_ratio(right_eye)


def calculate_average_ear(eye_pair):
    """Return the average EAR between the left and right eyes."""
    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must provide both left and right eyes.")

    left_ear = calculate_left_eye_ear(eye_pair)
    right_ear = calculate_right_eye_ear(eye_pair)
    return (left_ear + right_ear) / 2.0


def classify_eye_state(ear_value, open_threshold=0.22, closed_threshold=0.18):
    """Classify the eye as OPEN or CLOSED based on EAR threshold."""
    if np.isnan(ear_value):
        return "UNKNOWN"

    if ear_value >= open_threshold:
        return "OPEN"

    if ear_value <= closed_threshold:
        return "CLOSED"

    return "PARTIAL"


def detect_eye_state(eye_pair, open_threshold=0.22, closed_threshold=0.18):
    """Return a structured eye-state result from a pair of eyes.

    Example return:
    {
        "left_ear": 0.31,
        "right_ear": 0.29,
        "average_ear": 0.30,
        "eye_state": "OPEN"
    }
    """
    eye_pair = np.asarray(eye_pair, dtype=np.float32)

    if eye_pair.shape[0] < 2:
        raise ValueError("Eye pair must contain left and right eye landmarks.")

    left_ear = calculate_left_eye_ear(eye_pair)
    right_ear = calculate_right_eye_ear(eye_pair)
    average_ear = calculate_average_ear(eye_pair)

    eye_state = classify_eye_state(
        average_ear,
        open_threshold=open_threshold,
        closed_threshold=closed_threshold,
    )

    return {
        "left_ear": float(left_ear),
        "right_ear": float(right_ear),
        "average_ear": float(average_ear),
        "eye_state": eye_state,
    }
