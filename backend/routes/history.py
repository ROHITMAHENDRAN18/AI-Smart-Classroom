from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db

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


router = APIRouter(
    prefix="/history",
    tags=["History"],
)


@router.get(
    "/sessions",
    response_model=list[SessionHistoryResponse],
)
def list_history_sessions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100",
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="offset must be >= 0",
        )

    return get_all_sessions(
        db,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionHistoryResponse,
)
def get_history_session(
    session_id: str,
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

    return session


@router.get(
    "/sessions/{session_id}/attendance",
    response_model=list[AttendanceHistoryResponse],
)
def get_history_attendance(
    session_id: str,
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

    return get_session_attendance(
        db,
        session_id,
    )


@router.get(
    "/sessions/{session_id}/attention",
    response_model=list[AttentionHistoryResponse],
)
def get_history_attention(
    session_id: str,
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

    return get_session_attention(
        db,
        session_id,
    )


@router.get(
    "/sessions/{session_id}/summary",
    response_model=SessionSummaryResponse,
)
def get_history_summary(
    session_id: str,
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

    return summary