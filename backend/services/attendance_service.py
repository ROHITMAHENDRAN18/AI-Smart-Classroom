from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.attendance_record import AttendanceRecord


def record_attendance(
    db: Session,
    session_id: str,
    student_id: str,
    status: str = "PRESENT",
    confidence: float | None = None,
    recorded_at: datetime | None = None,
):
    existing_record = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
        .first()
    )

    if existing_record:
        existing_record.status = status
        existing_record.confidence = confidence

        if recorded_at is not None:
            existing_record.recorded_at = recorded_at

        db.commit()
        db.refresh(existing_record)

        return existing_record

    attendance_record = AttendanceRecord(
        session_id=session_id,
        student_id=student_id,
        status=status,
        confidence=confidence,
        recorded_at=recorded_at,
    )

    db.add(attendance_record)
    db.commit()
    db.refresh(attendance_record)

    return attendance_record


def get_attendance_for_session(
    db: Session,
    session_id: str,
):
    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .order_by(AttendanceRecord.recorded_at.asc())
        .all()
    )


def get_student_attendance(
    db: Session,
    session_id: str,
    student_id: str,
):
    return (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
        .first()
    )


def delete_attendance_for_session(
    db: Session,
    session_id: str,
):
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .all()
    )

    for record in records:
        db.delete(record)

    db.commit()

    return len(records)