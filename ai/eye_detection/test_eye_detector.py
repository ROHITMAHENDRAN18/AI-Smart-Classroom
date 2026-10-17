import os
import cv2
import numpy as np
import pytest

from ai.eye_detection.eye_detector import (
    calculate_average_ear,
    calculate_eye_aspect_ratio,
    calculate_left_eye_ear,
    calculate_right_eye_ear,
    classify_eye_state,
    detect_eye_state,
    detect_eye_state_from_face,
    extract_eye_landmarks_from_face,
    get_face_mesh,
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
    assert classify_eye_state(0.20) == "PARTIAL"
    assert classify_eye_state(None) == "UNKNOWN"
    assert classify_eye_state(float("nan")) == "UNKNOWN"
    assert classify_eye_state(-0.1) == "UNKNOWN"


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
    assert state["eye_state"] in {"OPEN", "CLOSED", "PARTIAL"}
    assert "average_ear" in state
    assert state["reason"] is None


def test_five_keypoints_rejected_for_ear():
    # InsightFace 5 keypoints cannot be used for 6-point EAR
    five_kps = np.array([
        [10.0, 10.0],
        [20.0, 10.0],
        [15.0, 15.0],
        [12.0, 20.0],
        [18.0, 20.0],
    ], dtype=np.float32)

    with pytest.raises(ValueError, match="Five-point facial keypoints do not contain eye contour"):
        detect_eye_state(five_kps)


def test_input_validation_errors():
    with pytest.raises(ValueError):
        calculate_eye_aspect_ratio(None)
    with pytest.raises(ValueError):
        calculate_eye_aspect_ratio(np.zeros((4, 2)))
    with pytest.raises(ValueError):
        calculate_eye_aspect_ratio(np.array([[np.nan, 0]] * 6))


def test_face_crop_too_small_returns_unknown():
    tiny_crop = np.zeros((20, 20, 3), dtype=np.uint8)
    result = detect_eye_state_from_face(tiny_crop)
    assert result["eye_state"] == "UNKNOWN"
    assert result["left_ear"] is None
    assert "too small" in result["reason"].lower()


def test_none_face_crop_returns_unknown():
    result = detect_eye_state_from_face(None)
    assert result["eye_state"] == "UNKNOWN"
    assert result["reason"] is not None


def test_real_student_image_detection():
    image_path = "datasets/students/24AD095/2.jpg"
    if os.path.exists(image_path):
        img = cv2.imread(image_path)
        assert img is not None
        if not hasattr(cv2, "CascadeClassifier"):
            pytest.skip("Installed OpenCV build has no cascade or FaceMesh support")
        result = detect_eye_state_from_face(img)
        if get_face_mesh() is None:
            assert result["eye_state"] == "UNKNOWN"
            assert result["left_ear"] is None
            assert result["right_ear"] is None
        else:
            assert result["eye_state"] in {"OPEN", "PARTIAL"}
            assert result["left_ear"] is not None
            assert result["right_ear"] is not None
            assert result["average_ear"] > 0.20
