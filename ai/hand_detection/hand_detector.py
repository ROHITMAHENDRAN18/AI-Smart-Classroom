"""Standalone hand detector based on MediaPipe hand landmarks.

This module intentionally remains independent of the live classroom pipeline
until the detector itself has been validated.
"""

from __future__ import annotations


HAND_OPEN_THRESHOLD = 0.25
HAND_LANDMARK_COUNT = 21


def hand_is_raised(hand_landmarks, wrist_index=0, index_tip_index=8, middle_tip_index=12):
    """Determine whether a hand is raised from 21 MediaPipe landmarks.

    A simple heuristic: the wrist is below the finger tips, and the fingertip is
    significantly above the wrist.
    """
    if not hand_landmarks or len(hand_landmarks) < HAND_LANDMARK_COUNT:
        return False, "NO_HAND", 0.0

    wrist = hand_landmarks[wrist_index]
    index_tip = hand_landmarks[index_tip_index]
    middle_tip = hand_landmarks[middle_tip_index]

    if wrist is None or index_tip is None or middle_tip is None:
        return False, "NO_HAND", 0.0

    wrist_y = wrist.y
    index_y = index_tip.y
    middle_y = middle_tip.y

    score = float(max(0.0, wrist_y - min(index_y, middle_y)))
    raised = score > HAND_OPEN_THRESHOLD

    if raised:
        return True, "RAISED", score

    return False, "LOW", score


def get_hand_side(hand_landmarks, wrist_index=0, thumb_tip_index=4, index_tip_index=8):
    """Determine whether the detected hand is LEFT or RIGHT from landmark geometry."""
    if not hand_landmarks or len(hand_landmarks) < HAND_LANDMARK_COUNT:
        return "NO_HAND"

    wrist = hand_landmarks[wrist_index]
    thumb_tip = hand_landmarks[thumb_tip_index]
    index_tip = hand_landmarks[index_tip_index]

    if wrist is None or thumb_tip is None or index_tip is None:
        return "NO_HAND"

    thumb_x = thumb_tip.x
    index_x = index_tip.x
    wrist_x = wrist.x

    if thumb_x < wrist_x and index_x < wrist_x:
        return "LEFT"

    if thumb_x > wrist_x and index_x > wrist_x:
        return "RIGHT"

    if index_x < wrist_x:
        return "LEFT"

    if index_x > wrist_x:
        return "RIGHT"

    return "UNKNOWN"


def classify_hand_state(left_raised, right_raised):
    """Return one of NO_HAND, LEFT, RIGHT, BOTH."""
    if left_raised and right_raised:
        return "BOTH"
    if left_raised:
        return "LEFT"
    if right_raised:
        return "RIGHT"
    return "NO_HAND"


def detect_hand_state(hand_landmarks, side=None):
    """Return a consistent hand-state object.

    Example:
    {
        'hand_detected': True,
        'hand_raised': True,
        'hand_side': 'RIGHT',
        'confidence': 0.91
    }
    """
    if not hand_landmarks or len(hand_landmarks) < HAND_LANDMARK_COUNT:
        return {
            'hand_detected': False,
            'hand_raised': False,
            'hand_side': 'NO_HAND',
            'confidence': 0.0,
        }

    raised, _, score = hand_is_raised(hand_landmarks)
    detected_side = side if side is not None else get_hand_side(hand_landmarks)

    if detected_side == 'NO_HAND':
        return {
            'hand_detected': False,
            'hand_raised': False,
            'hand_side': 'NO_HAND',
            'confidence': 0.0,
        }

    return {
        'hand_detected': True,
        'hand_raised': bool(raised),
        'hand_side': detected_side,
        'confidence': float(score),
    }
