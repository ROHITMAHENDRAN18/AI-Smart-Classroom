from types import SimpleNamespace

import numpy as np

from ai.face_recognition.face_track_association import (
    calculate_distance,
    clip_box,
    estimate_attention,
)


def _face(nose_x=50.0, landmarks=None):
    if landmarks is None:
        landmarks = [
            [20.0, 20.0],
            [80.0, 20.0],
            [nose_x, 50.0],
            [35.0, 80.0],
            [65.0, 80.0],
        ]
    return SimpleNamespace(kps=np.asarray(landmarks, dtype=np.float32))


def test_front_facing_face_is_attentive():
    state, yaw_ratio, pitch_ratio = estimate_attention(_face())

    assert state == "ATTENTIVE"
    assert yaw_ratio == 0.0
    assert 0.25 <= pitch_ratio <= 0.72


def test_face_turn_beyond_yaw_threshold_is_not_attentive():
    state, yaw_ratio, _ = estimate_attention(_face(nose_x=67.0))

    assert state == "NOT ATTENTIVE"
    assert yaw_ratio > 0.22


def test_missing_and_insufficient_landmarks_are_unknown():
    assert estimate_attention(None) == ("UNKNOWN", None, None)
    assert estimate_attention(SimpleNamespace(kps=None)) == ("UNKNOWN", None, None)
    assert estimate_attention(_face(landmarks=[[1.0, 2.0]] * 4)) == (
        "UNKNOWN",
        None,
        None,
    )


def test_degenerate_eye_geometry_is_unknown():
    landmarks = [
        [50.0, 20.0],
        [51.0, 20.0],
        [50.5, 40.0],
        [45.0, 60.0],
        [55.0, 60.0],
    ]

    assert estimate_attention(_face(landmarks=landmarks)) == (
        "UNKNOWN",
        None,
        None,
    )


def test_distance_and_box_clipping_helpers():
    assert calculate_distance([0, 0], [3, 4]) == 5.0
    assert clip_box(-5, 10, 110, 90, width=100, height=80) == (0, 10, 99, 79)
