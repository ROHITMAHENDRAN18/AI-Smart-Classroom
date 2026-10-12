from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.models.attendance_record import AttendanceRecord
from backend.models.classroom_session import ClassroomSession
from backend.models.student import Student
from backend.schemas.classroom_data import (
    ClassroomAttendanceRecord,
    ClassroomAttendanceResponse,
    DailyAttendanceSummary,
)


def _attendance_query(db: Session, classroom_id: int):
    return (
        db.query(AttendanceRecord, Student.name)
        .join(
            ClassroomSession,
            ClassroomSession.session_id == AttendanceRecord.session_id,
        )
        .outerjoin(
            Student,
            Student.student_id == AttendanceRecord.student_id,
        )
        .filter(ClassroomSession.classroom_id == classroom_id)
    )


def get_classroom_attendance(
    db: Session,
    classroom_id: int,
    *,
    from_date: date,
    to_date: date,
    session_id: str | None,
    limit: int,
    offset: int,
) -> ClassroomAttendanceResponse:
    start_at = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(
        to_date + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    if session_id is not None:
        session_exists = (
            db.query(ClassroomSession.id)
            .filter(
                ClassroomSession.classroom_id == classroom_id,
                ClassroomSession.session_id == session_id,
            )
            .first()
        )
        if session_exists is None:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Classroom session not found",
            )

    query = _attendance_query(db, classroom_id).filter(
        AttendanceRecord.recorded_at >= start_at,
        AttendanceRecord.recorded_at < end_at,
    )
    if session_id is not None:
        query = query.filter(AttendanceRecord.session_id == session_id)

    normalized_status = func.upper(AttendanceRecord.status)
    present_expression = case((normalized_status == "PRESENT", 1), else_=0)
    absent_expression = case((normalized_status == "ABSENT", 1), else_=0)
    totals = (
        query.with_entities(
            func.count(AttendanceRecord.id),
            func.sum(present_expression),
            func.sum(absent_expression),
        )
        .one()
    )
    total_records = int(totals[0] or 0)
    present_count = int(totals[1] or 0)
    absent_count = int(totals[2] or 0)
    unknown_count = total_records - present_count - absent_count
    denominator = present_count + absent_count
    attendance_rate = (
        round(present_count / denominator * 100, 2)
        if denominator
        else None
    )

    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        trend_date = func.date(func.timezone("UTC", AttendanceRecord.recorded_at))
    else:
        trend_date = func.date(AttendanceRecord.recorded_at)

    daily_rows = (
        query.with_entities(
            trend_date.label("record_date"),
            func.count(AttendanceRecord.id),
            func.sum(present_expression),
            func.sum(absent_expression),
        )
        .group_by(trend_date)
        .order_by(trend_date)
        .all()
    )
    daily_trend = []
    for row in daily_rows:
        day_value = row[0]
        if isinstance(day_value, str):
            day_value = date.fromisoformat(day_value)
        elif isinstance(day_value, datetime):
            day_value = day_value.date()
        daily_total = int(row[1] or 0)
        daily_present = int(row[2] or 0)
        daily_absent = int(row[3] or 0)
        daily_trend.append(
            DailyAttendanceSummary(
                date=day_value,
                total_records=daily_total,
                present_count=daily_present,
                absent_count=daily_absent,
                unknown_count=daily_total - daily_present - daily_absent,
            )
        )

    rows = (
        query.order_by(
            AttendanceRecord.recorded_at.desc(),
            AttendanceRecord.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    records = [
        ClassroomAttendanceRecord(
            id=record.id,
            session_id=record.session_id,
            student_id=record.student_id,
            student_name=student_name,
            status=record.status,
            confidence=record.confidence,
            recorded_at=record.recorded_at,
        )
        for record, student_name in rows
    ]

    return ClassroomAttendanceResponse(
        classroom_id=classroom_id,
        from_date=from_date,
        to_date=to_date,
        generated_at=datetime.now(timezone.utc),
        total_records=total_records,
        present_count=present_count,
        absent_count=absent_count,
        unknown_count=unknown_count,
        attendance_rate=attendance_rate,
        limit=limit,
        offset=offset,
        records=records,
        daily_trend=daily_trend,
    )
