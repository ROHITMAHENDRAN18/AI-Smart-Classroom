"""Standalone head-pose detector based on the current InsightFace landmark layout.

This module intentionally mirrors the live `face.kps` geometry used by the
existing attention estimator in `ai/face_recognition/face_track_association.py`.
It is designed to be independently testable before any live integration.
"""

from __future__ import annotations

import numpy as np


def calculate_yaw_ratio(landmarks):
    """Compute the normalized horizontal head-turn ratio from 5 landmarks."""
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 5:
        raise ValueError("At least 5 facial landmarks are required.")

    left_eye, right_eye, nose, _, _ = points[:5]
    eye_center = (left_eye + right_eye) / 2.0
    eye_distance = np.linalg.norm(left_eye - right_eye)

    if eye_distance <= 1e-8:
        return 0.0

    horizontal_offset = abs(float(nose[0] - eye_center[0]))
    return horizontal_offset / eye_distance


def calculate_pitch_ratio(landmarks):
    """Compute the normalized vertical head-tilt ratio from 5 landmarks."""
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 5:
        raise ValueError("At least 5 facial landmarks are required.")

    left_eye, right_eye, nose, left_mouth, right_mouth = points[:5]
    eye_center = (left_eye + right_eye) / 2.0
    mouth_center = (left_mouth + right_mouth) / 2.0
    face_vertical_distance = np.linalg.norm(eye_center - mouth_center)

    if face_vertical_distance <= 1e-8:
        return 0.0

    vertical_offset = float(nose[1] - eye_center[1])
    return vertical_offset / face_vertical_distance


def classify_head_pose(yaw_ratio, pitch_ratio, horizontal_offset=0.0, vertical_offset=0.0):
    """Classify the head pose using yaw and pitch ratios.

    This intentionally mirrors the same ratio-based logic already used by the
    current attention estimator: a face is considered front-facing when both
    yaw and pitch stay within a compact region, and any significant drift is
    classified as left/right/up/down.
    """
    if np.isnan(yaw_ratio) or np.isnan(pitch_ratio):
        return "UNKNOWN"

    if vertical_offset < -0.25:
        return "UP"

    if vertical_offset > 0.25:
        return "DOWN"

    if horizontal_offset < -0.12:
        return "LEFT"

    if horizontal_offset > 0.12:
        return "RIGHT"

    if yaw_ratio <= 0.22 and abs(pitch_ratio) <= 0.30:
        return "FRONT"

    return "FRONT"


def calculate_head_pose(landmarks):
    """Return yaw, pitch, and pose classification for a face landmark set."""
    points = np.asarray(landmarks, dtype=np.float32)

    if points.shape[0] < 5:
        raise ValueError("At least 5 facial landmarks are required.")

    left_eye, right_eye, nose, left_mouth, right_mouth = points[:5]
    eye_center = (left_eye + right_eye) / 2.0
    mouth_center = (left_mouth + right_mouth) / 2.0
    eye_distance = np.linalg.norm(left_eye - right_eye)
    face_vertical_distance = np.linalg.norm(eye_center - mouth_center)

    if eye_distance <= 1e-8 or face_vertical_distance <= 1e-8:
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "head_pose": "UNKNOWN",
            "yaw_ratio": 0.0,
            "pitch_ratio": 0.0,
        }

    yaw_ratio = calculate_yaw_ratio(points)
    pitch_ratio = calculate_pitch_ratio(points)
    horizontal_offset = float(nose[0] - eye_center[0]) / eye_distance
    vertical_offset = float(nose[1] - eye_center[1]) / face_vertical_distance

    head_pose = classify_head_pose(
        yaw_ratio,
        pitch_ratio,
        horizontal_offset=horizontal_offset,
        vertical_offset=vertical_offset,
    )

    return {
        "yaw": float(yaw_ratio),
        "pitch": float(pitch_ratio),
        "head_pose": head_pose,
        "yaw_ratio": float(yaw_ratio),
        "pitch_ratio": float(pitch_ratio),
    }


def detect_head_pose(landmarks):
    """Alias for `calculate_head_pose` to keep the API consistent across modules."""
    return calculate_head_pose(landmarks)
