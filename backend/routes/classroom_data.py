from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth.classroom_access import require_classroom_access
from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.classroom_data import (
    ClassroomAttendanceResponse,
    ManualAttendanceRequest,
)
from backend.schemas.history import AttendanceHistoryResponse
from backend.services.classroom_data_service import (
    get_classroom_attendance,
    mark_manual_session_attendance,
)
from backend.utils.date_range import get_utc_date_range
from backend.utils.logger import logger


router = APIRouter(
    prefix="/classrooms",
    tags=["Classroom Data"],
)


@router.post(
    "/{classroom_id}/sessions/{session_id}/attendance/manual",
    response_model=list[AttendanceHistoryResponse],
)
def mark_manual_attendance(
    classroom_id: int,
    session_id: str,
    request: ManualAttendanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can mark classroom attendance.",
        )
    require_classroom_access(
        classroom_id,
        current_user,
        db,
        require_active=True,
    )

    try:
        return mark_manual_session_attendance(
            db,
            classroom_id,
            session_id,
            [
                (entry.student_id, entry.status)
                for entry in request.records
            ],
        )
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Database failure while marking manual attendance")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attendance data is temporarily unavailable.",
        ) from error


@router.post(
    "/{classroom_id}/sessions/{session_id}/attendance/detect-absentees",
    response_model=list[AttendanceHistoryResponse],
)
def auto_detect_absentees(
    classroom_id: int,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can mark classroom attendance.",
        )
    require_classroom_access(
        classroom_id,
        current_user,
        db,
        require_active=True,
    )

    try:
        from backend.services.attendance_service import mark_unmarked_as_absent

        return mark_unmarked_as_absent(
            db,
            classroom_id=classroom_id,
            session_id=session_id,
        )
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Database failure while detecting absentees")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attendance data is temporarily unavailable.",
        ) from error


@router.get(
    "/{classroom_id}/attendance",
    response_model=ClassroomAttendanceResponse,
)
def classroom_attendance(
    classroom_id: int,
    date_filter: date | None = Query(default=None, alias="date"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session_id: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_classroom_access(
        classroom_id,
        current_user,
        db,
        require_active=True,
    )

    if date_filter is not None and (from_date is not None or to_date is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Use either date or from_date/to_date, not both.",
        )
    if date_filter is not None:
        from_date = date_filter
        to_date = date_filter
    elif from_date is None and to_date is None:
        today = datetime.now(timezone.utc).date()
        from_date = today
        to_date = today

    get_utc_date_range(from_date, to_date)
    if from_date is None or to_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Both from_date and to_date are required for a date range.",
        )

    try:
        return get_classroom_attendance(
            db,
            classroom_id,
            from_date=from_date,
            to_date=to_date,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Database failure while retrieving classroom attendance")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Classroom attendance data is temporarily unavailable.",
        ) from error
