from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.classroom_session import ClassroomSession


def create_classroom_session(
    db: Session,
    session_id: str,
    started_at: datetime,
):
    existing_session = (
        db.query(ClassroomSession)
        .filter(ClassroomSession.session_id == session_id)
        .first()
    )

    if existing_session:
        return existing_session

    classroom_session = ClassroomSession(
        session_id=session_id,
        started_at=started_at,
        status="ACTIVE",
    )

    db.add(classroom_session)
    db.commit()
    db.refresh(classroom_session)

    return classroom_session


def get_classroom_session(
    db: Session,
    session_id: str,
):
    return (
        db.query(ClassroomSession)
        .filter(ClassroomSession.session_id == session_id)
        .first()
    )


def finish_classroom_session(
    db: Session,
    session_id: str,
    ended_at: datetime,
    duration_seconds: int,
):
    classroom_session = get_classroom_session(
        db,
        session_id,
    )

    if classroom_session is None:
        return None

    classroom_session.ended_at = ended_at
    classroom_session.duration_seconds = duration_seconds
    classroom_session.status = "COMPLETED"

    db.commit()
    db.refresh(classroom_session)

    return classroom_session


def get_all_classroom_sessions(
    db: Session,
):
    return (
        db.query(ClassroomSession)
        .order_by(ClassroomSession.started_at.desc())
        .all()
    )