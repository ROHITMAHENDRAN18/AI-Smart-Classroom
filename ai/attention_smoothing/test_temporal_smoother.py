import math

import pytest

from ai.attention_smoothing.temporal_smoother import AttentionTemporalSmoother


def _update(smoother, track_id, state, score=0.9, confidence=0.9):
    return smoother.update(
        track_id=track_id,
        attention_state=state,
        attention_score=score,
        confidence=confidence,
    )


def test_unknown_without_history_returns_unknown():
    smoother = AttentionTemporalSmoother()

    result = _update(smoother, 1, "UNKNOWN", score=None, confidence=0.0)

    assert result.attention_state == "UNKNOWN"
    assert result.attention_score is None
    assert result.confidence == 0.0
    assert result.sample_count == 0
    assert result.stable is False


def test_first_observation_is_not_stable():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)

    result = _update(smoother, 1, "ATTENTIVE")

    assert result.attention_state == "UNKNOWN"
    assert result.sample_count == 1
    assert result.stable is False


def test_consistent_observations_become_stable():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)

    for _ in range(3):
        result = _update(smoother, 1, "ATTENTIVE")

    assert result.attention_state == "ATTENTIVE"
    assert result.sample_count == 3
    assert result.stable is True


def test_unstable_confidence_is_reduced():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)

    result = _update(smoother, 1, "ATTENTIVE", confidence=0.9)

    assert result.attention_state == "UNKNOWN"
    assert result.confidence == pytest.approx(0.45)
    assert result.stable is False


def test_partial_is_a_real_state_after_consensus():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)

    for _ in range(3):
        result = _update(smoother, 1, "PARTIAL")

    assert result.attention_state == "PARTIAL"
    assert result.stable is True


def test_single_bad_frame_does_not_flip_stable_state():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)
    for _ in range(3):
        _update(smoother, 1, "ATTENTIVE")

    result = _update(smoother, 1, "NOT ATTENTIVE", score=0.2)

    assert result.attention_state == "ATTENTIVE"
    assert result.stable is True


def test_majority_change_eventually_changes_state():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)
    states = ["ATTENTIVE", "NOT ATTENTIVE", "NOT ATTENTIVE", "NOT ATTENTIVE"]

    for state in states:
        result = _update(smoother, 1, state, score=0.2 if state == "NOT ATTENTIVE" else 0.9)

    assert result.attention_state == "NOT ATTENTIVE"
    assert result.stable is True


def test_track_histories_are_independent():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)

    for _ in range(3):
        attentive = _update(smoother, 1, "ATTENTIVE")
        not_attentive = _update(smoother, 2, "NOT ATTENTIVE", score=0.1)

    assert attentive.attention_state == "ATTENTIVE"
    assert not_attentive.attention_state == "NOT ATTENTIVE"


def test_unknown_observation_does_not_consume_or_change_history():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=3)
    for _ in range(3):
        _update(smoother, 1, "ATTENTIVE")
    history_before = smoother.get_history(1)

    result = _update(smoother, 1, "UNKNOWN", score=None, confidence=0.0)

    assert smoother.get_history(1) == history_before
    assert result.attention_state == "ATTENTIVE"
    assert result.sample_count == 3
    assert result.stable is True


def test_score_uses_exponentially_weighted_recent_observations():
    smoother = AttentionTemporalSmoother(window_size=5, minimum_samples=2, score_decay=0.8)
    _update(smoother, 1, "ATTENTIVE", score=1.0, confidence=1.0)

    result = _update(smoother, 1, "NOT ATTENTIVE", score=0.0, confidence=1.0)

    assert result.attention_score == pytest.approx(0.8 / 1.8, abs=1e-4)


def test_history_is_bounded_by_window_size():
    smoother = AttentionTemporalSmoother(window_size=3, minimum_samples=2)
    for state in ("ATTENTIVE", "ATTENTIVE", "NOT ATTENTIVE", "NOT ATTENTIVE"):
        result = _update(smoother, 1, state)

    assert len(smoother.get_history(1)) == 3
    assert result.attention_state == "NOT ATTENTIVE"


def test_scores_and_confidence_are_clamped():
    smoother = AttentionTemporalSmoother(window_size=2, minimum_samples=1)

    result = smoother.update(1, "ATTENTIVE", attention_score=5.0, confidence=-1.0)

    assert result.attention_score == 1.0
    assert result.confidence == 0.0


def test_invalid_state_is_rejected():
    smoother = AttentionTemporalSmoother()

    with pytest.raises(ValueError):
        _update(smoother, 1, "DISTRACTED")


def test_non_finite_values_are_rejected():
    smoother = AttentionTemporalSmoother()

    with pytest.raises(ValueError):
        smoother.update(1, "ATTENTIVE", attention_score=math.nan, confidence=0.5)

    with pytest.raises(ValueError):
        smoother.update(1, "ATTENTIVE", attention_score=0.5, confidence=math.inf)


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        AttentionTemporalSmoother(window_size=0)
    with pytest.raises(ValueError):
        AttentionTemporalSmoother(window_size=3, minimum_samples=4)
    with pytest.raises(ValueError):
        AttentionTemporalSmoother(state_threshold=0)
    with pytest.raises(ValueError):
        AttentionTemporalSmoother(score_decay=1.1)


def test_clear_track_and_retain_active_tracks():
    smoother = AttentionTemporalSmoother()
    _update(smoother, 1, "ATTENTIVE")
    _update(smoother, 2, "NOT ATTENTIVE")

    removed_count = smoother.retain_tracks({1})

    assert removed_count == 1
    assert smoother.get_history(1)
    assert smoother.get_history(2) == []

    smoother.clear_track(1)
    assert smoother.get_history(1) == []


def test_clear_all_removes_every_track():
    smoother = AttentionTemporalSmoother()
    _update(smoother, 1, "ATTENTIVE")
    _update(smoother, 2, "NOT ATTENTIVE")

    smoother.clear_all()

    assert smoother.get_history(1) == []
    assert smoother.get_history(2) == []
