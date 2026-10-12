from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.analytics.student_analytics import (
    calculate_attendance_analytics,
    calculate_attention_analytics,
)
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord
from backend.models.classroom_member import ClassroomMember
from backend.models.classroom_session import ClassroomSession
from backend.models.student import Student


def _session_ids(db: Session, classroom_ids: list[int] | None):
    query = db.query(ClassroomSession.session_id)
    if classroom_ids is not None:
        query = query.filter(ClassroomSession.classroom_id.in_(classroom_ids))
    return query


def get_total_sessions(
    db: Session,
    classroom_ids: list[int] | None = None,
) -> int:
    query = db.query(func.count(ClassroomSession.id))
    if classroom_ids is not None:
        query = query.filter(ClassroomSession.classroom_id.in_(classroom_ids))
    return int(query.scalar() or 0)


def get_student_attended_sessions(
    db: Session,
    student_id: str,
    classroom_ids: list[int] | None = None,
) -> int:
    query = (
        db.query(func.count(func.distinct(AttendanceRecord.session_id)))
        .filter(
            AttendanceRecord.student_id == student_id,
            func.lower(AttendanceRecord.status) == "present",
            AttendanceRecord.session_id.in_(_session_ids(db, classroom_ids)),
        )
    )
    return int(query.scalar() or 0)


def get_student_info(db: Session, student_id: str):
    student = (
        db.query(Student.student_id, Student.name)
        .filter(Student.student_id == student_id)
        .first()
    )
    if student is None:
        return None
    return {"student_id": student.student_id, "name": student.name}


def get_student_attention_records(
    db: Session,
    student_id: str,
    classroom_ids: list[int] | None = None,
):
    rows = (
        db.query(
            AttentionRecord.attention_state,
            AttentionRecord.attention_score,
            AttentionRecord.recorded_at,
        )
        .filter(
            AttentionRecord.student_id == student_id,
            AttentionRecord.session_id.in_(_session_ids(db, classroom_ids)),
        )
        .order_by(AttentionRecord.recorded_at.asc())
        .all()
    )
    return [
        {
            "attention_state": row.attention_state,
            "attention_score": row.attention_score,
            "recorded_at": row.recorded_at,
        }
        for row in rows
    ]


def get_student_analytics(
    db: Session,
    student_id: str,
    classroom_ids: list[int] | None = None,
):
    student = get_student_info(db, student_id)
    total_sessions = get_total_sessions(db, classroom_ids)
    attended_sessions = get_student_attended_sessions(
        db,
        student_id,
        classroom_ids,
    )
    records = get_student_attention_records(
        db,
        student_id,
        classroom_ids,
    )
    attendance = calculate_attendance_analytics(
        student_id=student_id,
        total_sessions=total_sessions,
        attended_sessions=attended_sessions,
    )
    attention = calculate_attention_analytics(
        student_id=student_id,
        records=records,
    )
    return {
        "student_id": student_id,
        "student_name": student["name"] if student else None,
        "attendance": attendance,
        "attention": attention,
    }


def get_all_students_analytics(
    db: Session,
    classroom_ids: list[int] | None = None,
):
    query = db.query(Student.student_id).order_by(Student.student_id)
    if classroom_ids is not None:
        query = (
            query.join(
                ClassroomMember,
                ClassroomMember.student_id == Student.student_id,
            )
            .filter(
                ClassroomMember.classroom_id.in_(classroom_ids),
                ClassroomMember.is_active.is_(True),
            )
            .distinct()
        )

    return [
        get_student_analytics(db, student_id, classroom_ids)
        for (student_id,) in query.all()
    ]


def get_student_attention_timeline(
    db: Session,
    student_id: str,
    classroom_ids: list[int] | None = None,
):
    query = (
        db.query(
            AttentionRecord.recorded_at,
            AttentionRecord.attention_state,
            AttentionRecord.attention_score,
            AttentionRecord.fusion_state,
            AttentionRecord.fusion_score,
            AttentionRecord.temporal_state,
            AttentionRecord.temporal_score,
            AttentionRecord.temporal_confidence,
            AttentionRecord.temporal_stable,
        )
        .filter(
            AttentionRecord.student_id == student_id,
            AttentionRecord.session_id.in_(_session_ids(db, classroom_ids)),
        )
        .order_by(AttentionRecord.recorded_at.asc())
    )
    return [
        {
            "recorded_at": row.recorded_at,
            "attention_state": row.attention_state,
            "attention_score": row.attention_score,
            "fusion_state": row.fusion_state,
            "fusion_score": row.fusion_score,
            "temporal_state": row.temporal_state,
            "temporal_score": row.temporal_score,
            "temporal_confidence": row.temporal_confidence,
            "temporal_stable": row.temporal_stable,
        }
        for row in query.all()
    ]


def get_classroom_analytics(
    db: Session,
    classroom_ids: list[int] | None = None,
):
    query = db.query(
        AttentionRecord.attention_state,
        AttentionRecord.attention_score,
    ).filter(AttentionRecord.session_id.in_(_session_ids(db, classroom_ids)))
    rows = query.all()
    records = [
        {
            "attention_state": state,
            "attention_score": score,
        }
        for state, score in rows
    ]
    summary = calculate_attention_analytics(
        student_id="",
        records=records,
    )
    return {
        "total_records": summary.total_records,
        "average_attention_score": summary.average_attention_score,
        "attention_percentage": summary.attention_percentage,
        "attentive_records": summary.attentive_records,
        "partial_records": summary.partial_records,
        "not_attentive_records": summary.not_attentive_records,
        "unknown_records": summary.unknown_records,
    }
