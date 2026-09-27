import numpy as np

from ai.eye_detection.eye_detector import (
    calculate_average_ear,
    calculate_eye_aspect_ratio,
    calculate_left_eye_ear,
    calculate_right_eye_ear,
    classify_eye_state,
    detect_eye_state,
)


def build_open_eye():
    return np.array([
        [0.0, 0.0],
        [-0.35, -1.0],
        [-0.90, -1.35],
        [-1.8, 0.0],
        [-0.90, 1.35],
        [-0.35, 1.0],
    ], dtype=np.float32)


def build_closed_eye():
    return np.array([
        [0.0, 0.0],
        [-0.20, -0.12],
        [-0.60, -0.10],
        [-1.8, 0.0],
        [-0.60, 0.10],
        [-0.20, 0.12],
    ], dtype=np.float32)


def test_calculate_eye_aspect_ratio_for_open_eye():
    eye = build_open_eye()
    ear = calculate_eye_aspect_ratio(eye)
    assert ear > 0.25


def test_calculate_eye_aspect_ratio_for_closed_eye():
    eye = build_closed_eye()
    ear = calculate_eye_aspect_ratio(eye)
    assert ear < 0.18


def test_eye_classification_states():
    assert classify_eye_state(0.30) == "OPEN"
    assert classify_eye_state(0.12) == "CLOSED"


def test_average_ear_and_detector_output():
    left_eye = build_open_eye()
    right_eye = build_closed_eye()

    left_ear = calculate_left_eye_ear(np.array([left_eye, right_eye]))
    right_ear = calculate_right_eye_ear(np.array([left_eye, right_eye]))
    average = calculate_average_ear(np.array([left_eye, right_eye]))

    assert left_ear > 0.25
    assert right_ear < 0.18
    assert average > 0.20

    state = detect_eye_state(np.array([left_eye, right_eye]))
    assert state["eye_state"] in {"OPEN", "CLOSED"}
    assert "average_ear" in state
