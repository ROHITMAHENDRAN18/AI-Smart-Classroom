from dataclasses import dataclass
from typing import Optional


@dataclass
class AttendanceAnalytics:
    student_id: str
    total_sessions: int
    attended_sessions: int
    attendance_percentage: float


@dataclass
class AttentionAnalytics:
    student_id: str
    total_records: int
    attentive_records: int
    partial_records: int
    not_attentive_records: int
    unknown_records: int
    average_attention_score: float
    attention_percentage: float


@dataclass
class StudentAnalytics:
    student_id: str
    student_name: Optional[str]
    attendance: AttendanceAnalytics
    attention: AttentionAnalytics


def calculate_percentage(value: int, total: int) -> float:
    if total <= 0:
        return 0.0

    return round(
        (value / total) * 100,
        2
    )


def calculate_attendance_analytics(
    student_id: str,
    total_sessions: int,
    attended_sessions: int
):
    attendance_percentage = calculate_percentage(
        attended_sessions,
        total_sessions
    )

    return AttendanceAnalytics(
        student_id=student_id,
        total_sessions=total_sessions,
        attended_sessions=attended_sessions,
        attendance_percentage=attendance_percentage
    )


def calculate_attention_analytics(
    student_id: str,
    records
):
    total_records = len(records)

    attentive_records = 0
    partial_records = 0
    not_attentive_records = 0
    unknown_records = 0

    raw_scores = []

    for record in records:

        state = (
            record.get("attention_state")
            or "UNKNOWN"
        ).strip().upper()

        state = state.replace("_", " ")

        if state == "NOTATTENTIVE":
            state = "NOT ATTENTIVE"

        if state == "ATTENTIVE":
            attentive_records += 1

        elif state == "PARTIAL":
            partial_records += 1

        elif state == "NOT ATTENTIVE":
            not_attentive_records += 1

        else:
            unknown_records += 1

        score = record.get("attention_score")

        if score is None:
            continue

        try:
            score = float(score)
        except (TypeError, ValueError):
            continue

        if 0.0 <= score <= 100.0:
            raw_scores.append(score)

    if raw_scores:

        if all(score <= 1.0 for score in raw_scores):
            normalized_scores = raw_scores

        else:
            normalized_scores = [
                score / 100.0
                for score in raw_scores
            ]

        average_attention_score = (
            sum(normalized_scores)
            / len(normalized_scores)
        )

    else:
        average_attention_score = 0.0

    attention_percentage = round(
        average_attention_score * 100,
        2
    )

    return AttentionAnalytics(
        student_id=student_id,
        total_records=total_records,
        attentive_records=attentive_records,
        partial_records=partial_records,
        not_attentive_records=not_attentive_records,
        unknown_records=unknown_records,
        average_attention_score=round(
            average_attention_score,
            4
        ),
        attention_percentage=attention_percentage
    )