from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.models.classroom_session import ClassroomSession
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord
from backend.models.classroom_member import ClassroomMember
from backend.models.student import Student


SUPPORTED_ATTENTION_STATES = {
    "LISTENING",
    "SLEEPING",
    "LOOKING_AWAY",
    "UNKNOWN",
}
LEGACY_ATTENTION_STATES = {
    "ATTENTIVE",
    "NOT ATTENTIVE",
    "PARTIAL",
}


def summarize_attention_observations(records):
    """Group persisted states; percentages use only supported observations."""
    state_counts = {state: 0 for state in sorted(SUPPORTED_ATTENTION_STATES)}
    data_quality_state_counts: dict[str, int] = {}

    for record in records:
        # Match the persisted/API field consumed by the Analytics page.
        raw_state = getattr(record, "attention_state", None)

        if raw_state is None:
            state = "NULL"
        else:
            state = str(raw_state).strip().upper()
            if not state:
                state = "EMPTY"
            elif state == "LOOKING AWAY":
                state = "LOOKING_AWAY"
            elif state in {"NOT_ATTENTIVE", "NOTATTENTIVE"}:
                state = "NOT ATTENTIVE"

        if state in state_counts:
            state_counts[state] += 1
            continue

        if state in LEGACY_ATTENTION_STATES:
            quality_label = f"LEGACY: {state}"
        else:
            quality_label = state
        data_quality_state_counts[quality_label] = (
            data_quality_state_counts.get(quality_label, 0) + 1
        )

    attentive_count = state_counts["LISTENING"]
    not_attentive_count = state_counts["SLEEPING"] + state_counts["LOOKING_AWAY"]
    unknown_count = state_counts["UNKNOWN"]
    valid_count = sum(state_counts.values())
    total_count = len(records)

    def percentage(count: int) -> float:
        return round(count / valid_count * 100, 2) if valid_count else 0.0

    return {
        "attention_records": total_count,
        "valid_attention_records": valid_count,
        "data_quality_records": total_count - valid_count,
        "data_quality_state_counts": data_quality_state_counts,
        "attention_state_counts": state_counts,
        "attentive_count": attentive_count,
        "not_attentive_count": not_attentive_count,
        "unknown_count": unknown_count,
        # Retained for clients of the older API; legacy PARTIAL values are
        # reported in data_quality_state_counts and never reclassified.
        "partial_count": 0,
        "attentive_percentage": percentage(attentive_count),
        "not_attentive_percentage": percentage(not_attentive_count),
        "unknown_percentage": percentage(unknown_count),
        "partial_percentage": 0.0,
    }


def get_all_sessions(
    db: Session,
    limit: int = 50,
    offset: int = 0,
):
    return (
        db.query(ClassroomSession)
        .order_by(ClassroomSession.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_session_by_id(
    db: Session,
    session_id: str,
):
    return (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.session_id == session_id
        )
        .first()
    )


def get_session_attendance(
    db: Session,
    session_id: str,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
):
    query = db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id
    )
    if start_at is not None:
        query = query.filter(AttendanceRecord.recorded_at >= start_at)
    if end_at is not None:
        query = query.filter(AttendanceRecord.recorded_at < end_at)
    return (
        query
        .order_by(
            AttendanceRecord.recorded_at.asc()
        )
        .all()
    )


def get_session_attention(
    db: Session,
    session_id: str,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
):
    query = db.query(AttentionRecord).filter(
        AttentionRecord.session_id == session_id
    )
    if start_at is not None:
        query = query.filter(AttentionRecord.recorded_at >= start_at)
    if end_at is not None:
        query = query.filter(AttentionRecord.recorded_at < end_at)
    return (
        query
        .order_by(
            AttentionRecord.recorded_at.asc()
        )
        .all()
    )


def get_session_summary(
    db: Session,
    session_id: str,
):
    classroom_session = get_session_by_id(
        db,
        session_id,
    )

    if classroom_session is None:
        return None

    attendance_records = get_session_attendance(
        db,
        session_id,
    )

    stored_attention_records = get_session_attention(
        db,
        session_id,
    )

    # AttentionRecord has a student_id but no recognition or classroom
    # verification snapshot. Only include registered students with a
    # classroom membership that existed when this session began. Membership
    # rows are retained when deactivated, so historical members remain valid.
    session_started_at = classroom_session.started_at
    if session_started_at.tzinfo is not None:
        session_started_at = session_started_at.astimezone(timezone.utc).replace(
            tzinfo=None
        )
    eligible_student_ids = {
        student_id
        for (student_id,) in (
            db.query(Student.student_id)
            .join(
                ClassroomMember,
                ClassroomMember.student_id == Student.student_id,
            )
            .filter(
                ClassroomMember.classroom_id == classroom_session.classroom_id,
                ClassroomMember.joined_at <= session_started_at,
                Student.face_registered.is_(True),
            )
            .all()
        )
    }
    attention_records = [
        record
        for record in stored_attention_records
        if record.student_id in eligible_student_ids
    ]
    unassigned_attention_records = (
        len(stored_attention_records) - len(attention_records)
    )

    unique_students = sorted(
        {
            record.student_id
            for record in attendance_records
        }
    )

    attention_statistics = summarize_attention_observations(attention_records)

    # Current active membership is the only roster snapshot this schema keeps.
    # Keep persisted statuses separate from missing records: an unmarked member
    # is not evidence of absence.
    enrolled_ids = {
        student_id
        for (student_id,) in (
            db.query(ClassroomMember.student_id)
            .filter(
                ClassroomMember.classroom_id == classroom_session.classroom_id,
                ClassroomMember.is_active.is_(True),
            )
            .all()
        )
    }
    attendance_by_student = {
        row.student_id: str(row.status or "").strip().upper()
        for row in attendance_records
        if row.student_id in enrolled_ids
    }
    present_students = sum(status == "PRESENT" for status in attendance_by_student.values())
    absent_students = sum(status == "ABSENT" for status in attendance_by_student.values())
    unknown_attendance_students = sum(
        status == "UNKNOWN" for status in attendance_by_student.values()
    )
    attendance_data_quality_students = sum(
        status not in {"PRESENT", "ABSENT", "UNKNOWN"}
        for status in attendance_by_student.values()
    )
    unmarked_students = max(
        0,
        len(enrolled_ids)
        - present_students
        - absent_students
        - unknown_attendance_students
        - attendance_data_quality_students,
    )

    return {
        "session": classroom_session,
        "attendance": attendance_records,
        "attention": attention_records,
        "statistics": {
            "unique_students": len(
                unique_students
            ),
            "student_ids": unique_students,
            "attendance_records": len(
                attendance_records
            ),
            "unassigned_attention_records": unassigned_attention_records,
            "enrolled_students": len(enrolled_ids),
            "present_students": present_students,
            "absent_students": absent_students,
            "unknown_attendance_students": unknown_attendance_students,
            "attendance_data_quality_students": attendance_data_quality_students,
            "unmarked_students": unmarked_students,
            **attention_statistics,
        },
    }
