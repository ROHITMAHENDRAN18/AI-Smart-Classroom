import numpy as np

from ai.hand_detection.hand_detector import (
    classify_hand_state,
    detect_hand_state,
    get_hand_side,
    hand_is_raised,
)


def make_landmarks(wrist_y=0.8, index_y=0.2, middle_y=0.25, wrist_x=0.5, index_x=0.7, middle_x=0.8):
    landmarks = [
        type('Point', (), {'x': wrist_x, 'y': wrist_y})() for _ in range(21)
    ]
    landmarks[0].x = wrist_x
    landmarks[0].y = wrist_y
    landmarks[8].x = index_x
    landmarks[8].y = index_y
    landmarks[12].x = middle_x
    landmarks[12].y = middle_y
    return landmarks


def test_hand_is_raised_detects_raised_hand():
    landmarks = make_landmarks(wrist_y=0.8, index_y=0.2, middle_y=0.25)
    raised, state, score = hand_is_raised(landmarks)
    assert raised is True
    assert state == "RAISED"
    assert score > 0.0


def test_get_hand_side_detects_right_hand():
    landmarks = make_landmarks(wrist_x=0.5, index_x=0.8, middle_x=0.9)
    assert get_hand_side(landmarks) == "RIGHT"


def test_get_hand_side_detects_left_hand():
    landmarks = make_landmarks(wrist_x=0.5, index_x=0.2, middle_x=0.1)
    assert get_hand_side(landmarks) == "LEFT"


def test_classify_hand_state_and_detect_hand_state():
    assert classify_hand_state(True, False) == "LEFT"
    assert classify_hand_state(False, True) == "RIGHT"
    assert classify_hand_state(True, True) == "BOTH"
    assert classify_hand_state(False, False) == "NO_HAND"

    state = detect_hand_state(make_landmarks(wrist_y=0.8, index_y=0.2, middle_y=0.25, wrist_x=0.5, index_x=0.8, middle_x=0.9))
    assert state["hand_detected"] is True
    assert state["hand_raised"] is True
    assert state["hand_side"] == "RIGHT"
