from backend.analytics.student_analytics import (
    calculate_percentage,
    calculate_attendance_analytics,
    calculate_attention_analytics,
)


def test_calculate_percentage():

    assert calculate_percentage(
        5,
        10
    ) == 50.0


def test_zero_percentage():

    assert calculate_percentage(
        0,
        0
    ) == 0.0


def test_attendance_analytics():

    result = calculate_attendance_analytics(
        student_id="24AD095",
        total_sessions=10,
        attended_sessions=8
    )

    assert result.student_id == "24AD095"
    assert result.total_sessions == 10
    assert result.attended_sessions == 8
    assert result.attendance_percentage == 80.0


def test_attention_analytics():

    records = [
        {
            "attention_state": "ATTENTIVE",
            "attention_score": 0.9,
        },
        {
            "attention_state": "PARTIAL",
            "attention_score": 0.5,
        },
        {
            "attention_state": "NOT ATTENTIVE",
            "attention_score": 0.2,
        },
        {
            "attention_state": "UNKNOWN",
            "attention_score": None,
        },
    ]

    result = calculate_attention_analytics(
        student_id="24AD095",
        records=records
    )

    assert result.total_records == 4
    assert result.attentive_records == 1
    assert result.partial_records == 1
    assert result.not_attentive_records == 1
    assert result.unknown_records == 1

    assert result.average_attention_score == 0.5333
    assert result.attention_percentage == 53.33