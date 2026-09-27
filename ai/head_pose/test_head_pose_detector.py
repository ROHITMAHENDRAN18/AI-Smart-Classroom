import numpy as np

from ai.head_pose.head_pose_detector import (
    calculate_head_pose,
    calculate_pitch_ratio,
    calculate_yaw_ratio,
    classify_head_pose,
)


def build_front_face():
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.0, 0.45],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_left_face():
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [-0.5, 0.45],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_right_face():
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [2.5, 0.45],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_up_face():
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.0, -1.3],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def build_down_face():
    return np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [1.0, 1.4],
        [0.4, 2.0],
        [1.6, 2.0],
    ], dtype=np.float32)


def test_yaw_and_pitch_values():
    front = build_front_face()
    yaw = calculate_yaw_ratio(front)
    pitch = calculate_pitch_ratio(front)

    assert yaw < 0.22
    assert abs(pitch) <= 0.30


def test_classify_front_left_right_up_down():
    assert classify_head_pose(0.05, 0.10, 0.0, 0.0) == "FRONT"
    assert classify_head_pose(0.30, 0.10, -0.25, 0.0) == "LEFT"
    assert classify_head_pose(0.30, 0.10, 0.25, 0.0) == "RIGHT"
    assert classify_head_pose(0.05, -0.30, 0.0, -0.30) == "UP"
    assert classify_head_pose(0.05, 0.40, 0.0, 0.40) == "DOWN"


def test_detect_head_pose_for_front_left_right_and_up_down():
    front_result = calculate_head_pose(build_front_face())
    left_result = calculate_head_pose(build_left_face())
    right_result = calculate_head_pose(build_right_face())
    up_result = calculate_head_pose(build_up_face())
    down_result = calculate_head_pose(build_down_face())

    assert front_result["head_pose"] == "FRONT"
    assert left_result["head_pose"] == "LEFT"
    assert right_result["head_pose"] == "RIGHT"
    assert up_result["head_pose"] == "UP"
    assert down_result["head_pose"] == "DOWN"

    assert "yaw" in front_result and "pitch" in front_result
