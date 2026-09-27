import pytest

from ai.attention_fusion.fusion_engine import AttentionFusionEngine


def test_fully_attentive_student():
    result = AttentionFusionEngine().fuse(
        eye_state="OPEN",
        head_pose="FRONT",
        emotion="NEUTRAL",
        phone_detected=False,
        hand_raised=False,
    )

    assert result.attention_state == "ATTENTIVE"
    assert result.attention_score >= 0.70
    assert result.confidence == pytest.approx(1.0)


def test_phone_detection_reduces_score_and_adds_reason():
    engine = AttentionFusionEngine()
    baseline = engine.fuse(
        eye_state="OPEN",
        head_pose="FRONT",
        emotion="NEUTRAL",
        phone_detected=False,
        hand_raised=False,
    )
    using_phone = engine.fuse(
        eye_state="OPEN",
        head_pose="FRONT",
        emotion="NEUTRAL",
        phone_detected=True,
        hand_raised=False,
    )

    assert using_phone.attention_score < baseline.attention_score
    assert "Phone detected." in using_phone.reasons


def test_closed_eyes_and_away_pose_reduce_attention():
    result = AttentionFusionEngine().fuse(
        eye_state="CLOSED",
        head_pose="LEFT",
        emotion="SAD",
        phone_detected=False,
        hand_raised=False,
    )

    assert result.attention_state == "NOT ATTENTIVE"
    assert "Eyes are closed." in result.reasons
    assert "Head is not facing forward." in result.reasons


def test_raised_hand_is_participation_not_distraction():
    result = AttentionFusionEngine().fuse(
        eye_state="OPEN",
        head_pose="FRONT",
        emotion="HAPPY",
        phone_detected=False,
        hand_raised=True,
    )

    assert result.attention_state == "ATTENTIVE"
    assert result.hand_raised is True
    assert "Hand raised." in result.reasons


def test_unavailable_signals_do_not_bias_score():
    result = AttentionFusionEngine().fuse()

    assert result.attention_state == "UNKNOWN"
    assert result.attention_score is None
    assert result.confidence == 0.0
    assert result.signal_scores == {}


def test_available_signal_is_scored_without_defaulting_missing_signals():
    result = AttentionFusionEngine().fuse(eye_state="OPEN")

    assert result.attention_state == "ATTENTIVE"
    assert result.attention_score == pytest.approx(1.0)
    assert result.confidence == pytest.approx(0.30)
    assert result.signal_scores == {"eye": 1.0}


def test_result_contains_only_observed_signal_scores():
    result = AttentionFusionEngine().fuse(
        eye_state="PARTIAL",
        head_pose="UNKNOWN",
        phone_detected=False,
    )

    assert result.signal_scores == {"eye": 0.5, "phone": 1.0}
    assert result.attention_score == pytest.approx((0.5 * 0.30 + 1.0 * 0.20) / 0.50)
    assert result.confidence == pytest.approx(0.50)


def test_custom_weights_are_normalized():
    engine = AttentionFusionEngine(
        eye_weight=3,
        head_pose_weight=3,
        emotion_weight=1,
        phone_weight=2,
        hand_weight=1,
    )

    assert sum(engine.weights.values()) == pytest.approx(1.0)


def test_invalid_weights_and_signal_values_are_rejected():
    with pytest.raises(ValueError):
        AttentionFusionEngine(eye_weight=0, head_pose_weight=0, emotion_weight=0, phone_weight=0, hand_weight=0)

    with pytest.raises(ValueError):
        AttentionFusionEngine(eye_weight=-1)

    with pytest.raises(ValueError):
        AttentionFusionEngine().fuse(eye_state="SQUINTING")

    with pytest.raises(ValueError):
        AttentionFusionEngine().fuse(phone_detected="false")
