from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom import Classroom
from backend.models.classroom_session import ClassroomSession
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.schemas.classroom_session import (
    ClassroomSessionResponse,
    SessionStartResponse,
    SessionStopResponse,
)


router = APIRouter(
    prefix="/classrooms",
    tags=["Classroom Sessions"],
)


def get_current_teacher(
    current_user: User,
    db: Session,
) -> Teacher:
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can manage classroom sessions",
        )

    teacher = (
        db.query(Teacher)
        .filter(Teacher.user_id == current_user.id)
        .first()
    )

    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found",
        )

    return teacher


def get_teacher_classroom(
    classroom_id: int,
    teacher_id: int,
    db: Session,
) -> Classroom:
    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == classroom_id,
            Classroom.teacher_id == teacher_id,
        )
        .first()
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )

    if not classroom.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Classroom is inactive",
        )

    return classroom


def generate_session_id() -> str:
    now = datetime.now(timezone.utc)
    return f"SESSION_{now.strftime('%Y%m%d_%H%M%S_%f')}"


@router.post(
    "/{classroom_id}/sessions",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_classroom_session(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    existing_active_session = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.classroom_id == classroom_id,
            ClassroomSession.status == "ACTIVE",
        )
        .first()
    )

    if existing_active_session is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active classroom session already exists",
        )

    now = datetime.now(timezone.utc)

    session = ClassroomSession(
        session_id=generate_session_id(),
        classroom_id=classroom_id,
        started_at=now,
        ended_at=None,
        duration_seconds=None,
        status="ACTIVE",
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session": session,
    }


@router.get(
    "/{classroom_id}/sessions/active",
    response_model=ClassroomSessionResponse,
)
def get_active_classroom_session(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    session = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.classroom_id == classroom_id,
            ClassroomSession.status == "ACTIVE",
        )
        .order_by(ClassroomSession.id.desc())
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active classroom session",
        )

    return session


@router.get(
    "/{classroom_id}/sessions",
    response_model=list[ClassroomSessionResponse],
)
def get_classroom_session_history(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    sessions = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.classroom_id == classroom_id,
        )
        .order_by(ClassroomSession.id.desc())
        .all()
    )

    return sessions


@router.get(
    "/{classroom_id}/sessions/{session_id}",
    response_model=ClassroomSessionResponse,
)
def get_classroom_session(
    classroom_id: int,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    session = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.session_id == session_id,
            ClassroomSession.classroom_id == classroom_id,
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom session not found",
        )

    return session


@router.post(
    "/{classroom_id}/sessions/{session_id}/stop",
    response_model=SessionStopResponse,
)
def stop_classroom_session(
    classroom_id: int,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    session = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.session_id == session_id,
            ClassroomSession.classroom_id == classroom_id,
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom session not found",
        )

    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Classroom session is already stopped",
        )

    ended_at = datetime.now(timezone.utc)

    session.ended_at = ended_at
    session.duration_seconds = max(
        0,
        int(
            (
                ended_at - session.started_at
            ).total_seconds()
        ),
    )
    session.status = "COMPLETED"

    db.commit()
    db.refresh(session)

    return {
        "session": session,
    }