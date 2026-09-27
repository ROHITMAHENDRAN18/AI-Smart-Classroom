import math

import pytest

from ai.student_attention.attention_scorer import StudentAttentionScorer


def test_stable_high_score_is_attentive():
    result = StudentAttentionScorer().calculate(
        student_id="24AD095",
        attention_score=0.90,
        stable=True,
        temporal_confidence=0.85,
    )

    assert result.student_id == "24AD095"
    assert result.attention_score == 90.0
    assert result.attention_state == "ATTENTIVE"
    assert result.stable is True


def test_stable_medium_score_is_partial():
    result = StudentAttentionScorer().calculate(
        student_id="24AD095",
        attention_score=0.55,
        stable=True,
        temporal_confidence=0.80,
    )

    assert result.attention_score == 55.0
    assert result.attention_state == "PARTIAL"


def test_stable_low_score_is_not_attentive():
    result = StudentAttentionScorer().calculate(
        student_id="24AD095",
        attention_score=0.20,
        stable=True,
        temporal_confidence=0.80,
    )

    assert result.attention_score == 20.0
    assert result.attention_state == "NOT ATTENTIVE"


def test_unstable_score_is_provisional_and_state_remains_unknown():
    result = StudentAttentionScorer().calculate(
        student_id="24AD095",
        attention_score=0.90,
        stable=False,
        temporal_confidence=0.25,
    )

    assert result.attention_score == 90.0
    assert result.attention_state == "UNKNOWN"
    assert result.stable is False


def test_missing_score_is_unknown():
    result = StudentAttentionScorer().calculate(
        student_id="24AD095",
        attention_score=None,
        stable=True,
        temporal_confidence=0.0,
    )

    assert result.attention_score is None
    assert result.attention_state == "UNKNOWN"
    assert result.stable is False


def test_scores_and_confidence_are_clamped():
    result = StudentAttentionScorer().calculate(
        student_id="24AD095",
        attention_score=1.5,
        stable=True,
        temporal_confidence=-0.5,
    )

    assert result.attention_score == 100.0
    assert result.attention_state == "ATTENTIVE"
    assert result.temporal_confidence == 0.0


def test_student_id_is_normalized_and_required():
    scorer = StudentAttentionScorer()
    result = scorer.calculate("  24AD095  ", 0.8, True, 0.8)
    assert result.student_id == "24AD095"

    with pytest.raises(ValueError):
        scorer.calculate("  ", 0.8, True, 0.8)


def test_invalid_thresholds_are_rejected():
    with pytest.raises(ValueError):
        StudentAttentionScorer(attentive_threshold=0.4, partial_threshold=0.6)
    with pytest.raises(ValueError):
        StudentAttentionScorer(attentive_threshold=math.inf)


def test_non_finite_inputs_are_rejected():
    scorer = StudentAttentionScorer()

    with pytest.raises(ValueError):
        scorer.calculate("24AD095", math.nan, True, 0.8)
    with pytest.raises(ValueError):
        scorer.calculate("24AD095", 0.8, True, math.inf)


def test_percentage_conversion():
    scorer = StudentAttentionScorer()

    assert scorer.calculate_score_percentage(0.8234) == 82.34
    assert scorer.calculate_score_percentage(None) is None
