from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth.classroom_access import (
    get_owned_classroom_ids,
    require_classroom_access,
)
from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom_session import ClassroomSession
from backend.models.user import User
from backend.schemas.history import (
    SessionHistoryResponse,
    AttendanceHistoryResponse,
    AttentionHistoryResponse,
    SessionSummaryResponse,
)

from backend.services.history_service import (
    get_all_sessions,
    get_session_by_id,
    get_session_attendance,
    get_session_attention,
    get_session_summary,
)
from backend.utils.date_range import get_utc_date_range


router = APIRouter(
    prefix="/history",
    tags=["History"],
)


@router.get(
    "/sessions",
    response_model=list[SessionHistoryResponse],
)
def list_history_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    classroom_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if classroom_id is not None:
        require_classroom_access(classroom_id, current_user, db)
        return (
            db.query(ClassroomSession)
            .filter(ClassroomSession.classroom_id == classroom_id)
            .order_by(ClassroomSession.started_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    classroom_ids = get_owned_classroom_ids(current_user, db)
    if classroom_ids is None:
        return get_all_sessions(db, limit=limit, offset=offset)
    if not classroom_ids:
        return []
    return (
        db.query(ClassroomSession)
        .filter(ClassroomSession.classroom_id.in_(classroom_ids))
        .order_by(ClassroomSession.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionHistoryResponse,
)
def get_history_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session_by_id(
        db,
        session_id,
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Classroom session not found",
        )

    require_classroom_access(session.classroom_id, current_user, db)
    return session


@router.get(
    "/sessions/{session_id}/attendance",
    response_model=list[AttendanceHistoryResponse],
)
def get_history_attendance(
    session_id: str,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session_by_id(
        db,
        session_id,
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Classroom session not found",
        )

    require_classroom_access(session.classroom_id, current_user, db)
    start_at, end_at = get_utc_date_range(from_date, to_date)
    return get_session_attendance(
        db,
        session_id,
        start_at=start_at,
        end_at=end_at,
    )


@router.get(
    "/sessions/{session_id}/attention",
    response_model=list[AttentionHistoryResponse],
)
def get_history_attention(
    session_id: str,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session_by_id(
        db,
        session_id,
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Classroom session not found",
        )

    require_classroom_access(session.classroom_id, current_user, db)
    start_at, end_at = get_utc_date_range(from_date, to_date)
    return get_session_attention(
        db,
        session_id,
        start_at=start_at,
        end_at=end_at,
    )


@router.get(
    "/sessions/{session_id}/summary",
    response_model=SessionSummaryResponse,
)
def get_history_summary(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = get_session_summary(
        db,
        session_id,
    )

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Classroom session not found",
        )

    require_classroom_access(
        summary["session"].classroom_id,
        current_user,
        db,
    )
    return summary