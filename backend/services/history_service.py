from sqlalchemy.orm import Session

from backend.models.classroom_session import ClassroomSession
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord


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
):
    return (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.session_id == session_id
        )
        .order_by(
            AttendanceRecord.recorded_at.asc()
        )
        .all()
    )


def get_session_attention(
    db: Session,
    session_id: str,
):
    return (
        db.query(AttentionRecord)
        .filter(
            AttentionRecord.session_id == session_id
        )
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

    attention_records = get_session_attention(
        db,
        session_id,
    )

    unique_students = sorted(
        {
            record.student_id
            for record in attendance_records
        }
    )

    attentive_count = sum(
        1
        for record in attention_records
        if record.attention_state == "ATTENTIVE"
    )

    not_attentive_count = sum(
        1
        for record in attention_records
        if record.attention_state == "NOT ATTENTIVE"
    )

    unknown_count = sum(
        1
        for record in attention_records
        if record.attention_state == "UNKNOWN"
    )

    total_attention_records = len(
        attention_records
    )

    if total_attention_records > 0:
        attentive_percentage = (
            attentive_count
            / total_attention_records
            * 100
        )

        not_attentive_percentage = (
            not_attentive_count
            / total_attention_records
            * 100
        )

        unknown_percentage = (
            unknown_count
            / total_attention_records
            * 100
        )
    else:
        attentive_percentage = 0.0
        not_attentive_percentage = 0.0
        unknown_percentage = 0.0

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
            "attention_records": total_attention_records,
            "attentive_count": attentive_count,
            "not_attentive_count": not_attentive_count,
            "unknown_count": unknown_count,
            "attentive_percentage": round(
                attentive_percentage,
                2,
            ),
            "not_attentive_percentage": round(
                not_attentive_percentage,
                2,
            ),
            "unknown_percentage": round(
                unknown_percentage,
                2,
            ),
        },
    }