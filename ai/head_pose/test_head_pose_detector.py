import math
import numpy as np
import pytest

from ai.head_pose.head_pose_detector import (
    calculate_head_pose,
    calculate_pitch_ratio,
    calculate_yaw_ratio,
    classify_head_pose,
    detect_head_pose,
)


def build_front_face():
    """Synthetic frontal face: eye center at (1.0, 0.0), mouth center at (1.0, 2.0),
    nose at (1.0, 0.90) yielding realistic pitch ~0.45 and yaw = 0.0.
    """
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.0, 0.90],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_left_face():
    """Synthetic face turned left (viewer perspective): nose shifted left."""
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [0.3, 0.90],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_right_face():
    """Synthetic face turned right (viewer perspective): nose shifted right."""
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.7, 0.90],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_up_face():
    """Synthetic face looking up: nose shifted upwards near eyes."""
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.0, 0.20],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_down_face():
    """Synthetic face looking down: nose shifted downwards near mouth."""
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.0, 1.55],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def test_yaw_and_pitch_values():
    front = build_front_face()
    yaw = calculate_yaw_ratio(front)
    pitch = calculate_pitch_ratio(front)

    assert yaw < 0.22
    assert 0.20 <= pitch <= 0.68


def test_classify_front_left_right_up_down():
    # Frontal within bounds
    assert classify_head_pose(0.05, 0.45, 0.0, 0.45) == "FRONT"
    # Turned left
    assert classify_head_pose(0.35, 0.45, -0.35, 0.45) == "LEFT"
    # Turned right
    assert classify_head_pose(0.35, 0.45, 0.35, 0.45) == "RIGHT"
    # Tilted up
    assert classify_head_pose(0.05, 0.10, 0.0, 0.10) == "UP"
    # Tilted down
    assert classify_head_pose(0.05, 0.75, 0.0, 0.75) == "DOWN"


def test_detect_head_pose_for_front_left_right_and_up_down():
    front_result = calculate_head_pose(build_front_face())
    left_result = calculate_head_pose(build_left_face())
    right_result = calculate_head_pose(build_right_face())
    up_result = calculate_head_pose(build_up_face())
    down_result = calculate_head_pose(build_down_face())

    assert front_result["head_pose"] == "FRONT"
    # The configured calibration sign reverses image-coordinate direction.
    assert left_result["head_pose"] == "RIGHT"
    assert right_result["head_pose"] == "LEFT"
    assert up_result["head_pose"] == "UP"
    assert down_result["head_pose"] == "DOWN"

    assert "yaw" in front_result and "pitch" in front_result
    assert "yaw_ratio" in front_result and "pitch_ratio" in front_result


def test_real_student_face_geometry_is_front():
    # Real student face geometry: eye distance 100px, nose-to-eye ~56px, centered
    real_face = np.array([
        [100.0, 100.0],
        [200.0, 100.0],
        [153.0, 156.0],
        [120.0, 200.0],
        [180.0, 200.0],
    ], dtype=np.float32)
    result = calculate_head_pose(real_face)
    assert result["head_pose"] == "FRONT"
    assert result["yaw_ratio"] < 0.22
    assert 0.20 <= result["pitch_ratio"] <= 0.68


def test_non_finite_and_degenerate_landmarks():
    assert calculate_head_pose(None)["head_pose"] == "UNKNOWN"
    assert calculate_head_pose([])["head_pose"] == "UNKNOWN"
    assert calculate_head_pose(np.zeros((3, 2)))["head_pose"] == "UNKNOWN"

    # NaN in points
    nan_face = build_front_face()
    nan_face[2, 0] = np.nan
    assert calculate_head_pose(nan_face)["head_pose"] == "UNKNOWN"

    # Inf in points
    inf_face = build_front_face()
    inf_face[0, 1] = np.inf
    assert calculate_head_pose(inf_face)["head_pose"] == "UNKNOWN"

    # Degenerate eye distance (zero distance between eyes)
    zero_dist_face = np.array([
        [1.0, 1.0],
        [1.0, 1.0],
        [1.0, 1.5],
        [0.5, 2.0],
        [1.5, 2.0],
    ], dtype=np.float32)
    assert calculate_head_pose(zero_dist_face)["head_pose"] == "UNKNOWN"


def test_no_unconditional_front_fallback():
    # Non-finite ratio inputs must return UNKNOWN, not FRONT
    assert classify_head_pose(float("nan"), 0.45) == "UNKNOWN"
    assert classify_head_pose(0.05, float("inf")) == "UNKNOWN"
    assert classify_head_pose(-1.0, 0.45) == "UNKNOWN"


def test_helper_ratio_exceptions():
    with pytest.raises(ValueError):
        calculate_yaw_ratio(None)
    with pytest.raises(ValueError):
        calculate_yaw_ratio([[0, 0], [1, 1]])
    with pytest.raises(ValueError):
        calculate_pitch_ratio(None)
    with pytest.raises(ValueError):
        calculate_pitch_ratio([[0, 0], [1, 1]])
