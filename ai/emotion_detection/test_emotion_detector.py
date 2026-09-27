import numpy as np

from ai.emotion_detection.emotion_detector import (
    classify_emotion,
    detect_emotion,
    estimate_emotion,
    mouth_openness_ratio,
)


def _make_landmarks():
    return np.array(
        [
            [0.35, 0.50],
            [0.42, 0.50],
            [0.48, 0.50],
            [0.55, 0.50],
            [0.62, 0.50],
            [0.30, 0.55],
            [0.40, 0.57],
            [0.50, 0.58],
            [0.60, 0.57],
            [0.70, 0.55],
            [0.30, 0.40],
            [0.40, 0.38],
            [0.50, 0.37],
            [0.60, 0.38],
            [0.70, 0.40],
            [0.35, 0.80],
            [0.50, 0.82],
            [0.65, 0.80],
        ],
        dtype=np.float32,
    )


def test_mouth_openness_ratio_works():
    landmarks = _make_landmarks()
    ratio = mouth_openness_ratio(landmarks)
    assert 0.0 < ratio < 1.0


def test_classify_emotion_happy():
    landmarks = _make_landmarks()
    mouth = landmarks[:18]
    mouth[15] = [0.30, 0.72]
    mouth[16] = [0.50, 0.80]
    mouth[17] = [0.70, 0.72]
    result = classify_emotion(landmarks)
    assert result == "HAPPY"


def test_classify_emotion_surprised():
    landmarks = _make_landmarks()
    mouth = landmarks[:18]
    mouth[15] = [0.30, 0.65]
    mouth[16] = [0.50, 0.92]
    mouth[17] = [0.70, 0.65]
    result = classify_emotion(landmarks)
    assert result == "SURPRISED"


def test_detect_emotion_returns_payload():
    landmarks = _make_landmarks()
    result = detect_emotion(landmarks)
    assert "emotion" in result
    assert "confidence" in result
    assert result["emotion"] in {"HAPPY", "SURPRISED", "NEUTRAL", "SAD", "ANGRY"}
    assert 0.0 <= result["confidence"] <= 1.0


def test_estimate_emotion_from_points():
    landmarks = _make_landmarks()
    emotion = estimate_emotion(landmarks)
    assert isinstance(emotion, str)
