from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.attendance_record import AttendanceRecord

from sqlalchemy.exc import IntegrityError


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

def record_automatic_attendance(
    db: Session,
    session_id: str,
    student_id: str,
    recorded_at: datetime | None = None,
):
    """Record verified student presence once per session."""
    existing_record = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
        .first()
    )

    if existing_record is not None:
        return existing_record, False

    attendance_record = AttendanceRecord(
        session_id=session_id,
        student_id=student_id,
        status="PRESENT",
        attendance_source="AUTO",
        recorded_at=recorded_at or datetime.now().astimezone(),
    )

    try:
        with db.begin_nested():
            db.add(attendance_record)
            db.flush()

        db.commit()
        db.refresh(attendance_record)
        return attendance_record, True

    except IntegrityError:
        # The savepoint protects the outer transaction.
        existing_record = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == student_id,
            )
            .first()
        )

        if existing_record is not None:
            return existing_record, False

        raise

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


def mark_unmarked_as_absent(
    db: Session,
    classroom_id: int,
    session_id: str,
    recorded_at: datetime | None = None,
) -> list[AttendanceRecord]:
    """Mark all active enrolled classroom members who have no attendance record as ABSENT."""
    from datetime import timezone
    from backend.models.classroom_member import ClassroomMember

    enrolled_student_ids = [
        row[0]
        for row in (
            db.query(ClassroomMember.student_id)
            .filter(
                ClassroomMember.classroom_id == classroom_id,
                ClassroomMember.is_active.is_(True),
            )
            .all()
        )
    ]

    if not enrolled_student_ids:
        return []

    existing_student_ids = set(
        row[0]
        for row in (
            db.query(AttendanceRecord.student_id)
            .filter(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id.in_(enrolled_student_ids),
            )
            .all()
        )
    )

    absent_ids = [sid for sid in enrolled_student_ids if sid not in existing_student_ids]
    if not absent_ids:
        return []

    now = recorded_at or datetime.now(timezone.utc)
    new_records = []
    for student_id in absent_ids:
        record = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            status="ABSENT",
            attendance_source="AUTO",
            confidence=None,
            recorded_at=now,
        )
        db.add(record)
        new_records.append(record)

    db.commit()
    for record in new_records:
        db.refresh(record)

    return new_records