from datetime import datetime, timedelta, timezone

import pytest

from ai.attention_engine.attention_classifier import (
    TemporalAttentionClassifier,
    classify_attention_observation,
    classify_attention_state,
)


def test_single_observation_states_are_evidence_based():
    assert classify_attention_state(eye_state="OPEN", head_pose="FRONT") == "LISTENING"
    assert classify_attention_state(eye_state="CLOSED", head_pose="FRONT") == "SLEEPING"
    assert classify_attention_state(eye_state="OPEN", head_pose="DOWN") == "SLEEPING"
    assert (
        classify_attention_state(eye_state="OPEN", head_pose="LEFT") == "LOOKING_AWAY"
    )
    assert classify_attention_state(eye_state="OPEN", head_pose="RIGHT") == "LOOKING_AWAY"
    assert classify_attention_state(eye_state="OPEN", head_pose="UP") == "LOOKING_AWAY"
    assert (
        classify_attention_state(eye_state="UNKNOWN", head_pose="UNKNOWN") == "UNKNOWN"
    )
    # A single boolean is not temporal mouth-motion evidence.
    assert classify_attention_state(
        eye_state="OPEN", head_pose="FRONT", mouth_motion=True
    ) == "LISTENING"


def test_sustained_evidence_required_and_track_histories_are_isolated():
    classifier = TemporalAttentionClassifier()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    results = [
        classifier.update(
            "s1", "student-a", "SLEEPING", start + timedelta(seconds=n * 2.5)
        )
        for n in range(3)
    ]
    assert [result["attention_state"] for result in results] == [
        "UNKNOWN",
        "UNKNOWN",
        "SLEEPING",
    ]
    assert (
        classifier.update("s1", "student-b", "SLEEPING", start)["attention_state"]
        == "UNKNOWN"
    )
    assert (
        classifier.update("s2", "student-a", "SLEEPING", start)["attention_state"]
        == "UNKNOWN"
    )


def test_brief_unknown_observation_does_not_erase_valid_temporal_evidence():
    classifier = TemporalAttentionClassifier()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = classifier.update("s1", "student-a", "UNKNOWN", start)
    assert first["attention_state"] == "UNKNOWN"
    assert first["sample_count"] == 0
    classifier.update("s1", "student-a", "LISTENING", start)
    classifier.update("s1", "student-a", "LISTENING", start + timedelta(seconds=2.5))
    unknown = classifier.update(
        "s1", "student-a", "UNKNOWN", start + timedelta(seconds=5)
    )
    assert unknown["attention_state"] == "UNKNOWN"
    assert unknown["sample_count"] == 2
    result = classifier.update(
        "s1", "student-a", "LISTENING", start + timedelta(seconds=7.5)
    )
    assert result["attention_state"] == "LISTENING"
    assert result["sample_count"] == 3
    classifier.clear_session("s1")
    assert not classifier._evidence


def test_unknown_gap_over_ten_seconds_restarts_temporal_evidence():
    classifier = TemporalAttentionClassifier()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    classifier.update("s1", "student-a", "LISTENING", start)
    result = classifier.update(
        "s1", "student-a", "UNKNOWN", start + timedelta(seconds=10.1)
    )
    assert result["attention_state"] == "UNKNOWN"
    assert result["sample_count"] == 0
    assert (
        classifier.update(
            "s1", "student-a", "LISTENING", start + timedelta(seconds=10.2)
        )["sample_count"]
        == 1
    )


def test_minimum_sample_count_and_duration_are_both_required():
    classifier = TemporalAttentionClassifier()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    states = [
        classifier.update(
            "s1", "student-a", "LISTENING", start + timedelta(seconds=offset)
        )
        for offset in (0, 1, 2)
    ]
    assert [result["attention_state"] for result in states] == [
        "UNKNOWN", "UNKNOWN", "UNKNOWN"
    ]
    final = classifier.update(
        "s1", "student-a", "LISTENING", start + timedelta(seconds=4)
    )
    assert final["attention_state"] == "LISTENING"


def test_missing_signals_have_specific_diagnostic_reasons():
    eye_missing = classify_attention_observation(
        eye_state="UNKNOWN", head_pose="FRONT"
    )
    assert eye_missing == {
        "attention_state": "UNKNOWN",
        "diagnostic_reasons": ["EYE_SIGNAL_UNAVAILABLE"],
    }

    pose_missing = classify_attention_observation(
        eye_state="OPEN", head_pose="UNKNOWN"
    )
    assert pose_missing == {
        "attention_state": "UNKNOWN",
        "diagnostic_reasons": ["HEAD_POSE_UNAVAILABLE"],
    }

    invalid = classify_attention_observation(
        eye_state="BROKEN", head_pose="NAN"
    )
    assert invalid["attention_state"] == "UNKNOWN"
    assert set(invalid["diagnostic_reasons"]) == {
        "EYE_SIGNAL_UNAVAILABLE",
        "HEAD_POSE_UNAVAILABLE",
    }

    conflicting = classify_attention_observation(
        eye_state="CLOSED", head_pose="LEFT"
    )
    assert conflicting == {
        "attention_state": "UNKNOWN",
        "diagnostic_reasons": ["CONFLICTING_SIGNALS"],
    }


@pytest.mark.parametrize(
    "eye_state,head_pose,expected",
    [("CLOSED", "FRONT", "SLEEPING"), ("OPEN", "DOWN", "SLEEPING")],
)
def test_sleeping_candidates_still_require_temporal_stability(
    eye_state, head_pose, expected
):
    classifier = TemporalAttentionClassifier()
    observation = classify_attention_state(eye_state=eye_state, head_pose=head_pose)
    assert observation == expected
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    results = [
        classifier.update("s1", "student-a", observation, start + timedelta(seconds=n * 2))
        for n in range(3)
    ]
    assert [result["attention_state"] for result in results] == [
        "UNKNOWN", "UNKNOWN", "SLEEPING"
    ]


def test_missing_mouth_motion_never_claims_talking():
    assert (
        classify_attention_state(eye_state="UNKNOWN", head_pose="UNKNOWN") == "UNKNOWN"
    )


def test_available_single_signal_can_support_its_own_behavior_class():
    assert classify_attention_state(eye_state="UNKNOWN", head_pose="LEFT") == "LOOKING_AWAY"
    assert classify_attention_state(eye_state="CLOSED", head_pose="UNKNOWN") == "SLEEPING"


def test_temporal_classifier_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        TemporalAttentionClassifier(minimum_samples=1)
    with pytest.raises(ValueError):
        TemporalAttentionClassifier(minimum_duration_seconds=float("nan"))
