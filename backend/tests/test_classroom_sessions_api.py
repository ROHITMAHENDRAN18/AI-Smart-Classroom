from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.database.base import Base
from backend.models.classroom import Classroom
from backend.models.classroom_session import ClassroomSession
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.routes.classroom_sessions import (
    get_active_classroom_session,
    get_classroom_session_history,
    start_classroom_session,
    stop_classroom_session,
)
from configs.settings import API_VERSION


@pytest.fixture
def session_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    user = User(
        id=1,
        username="teacher",
        email="teacher@example.test",
        password_hash="not-used",
        role="TEACHER",
        is_active=True,
    )
    db.add(user)
    db.flush()
    teacher = Teacher(
        user_id=user.id,
        teacher_id="T1",
        name="Teacher",
        department="Computing",
    )
    db.add(teacher)
    db.flush()
    classroom = Classroom(
        classroom_code="C1",
        name="Classroom 1",
        department="Computing",
        year=1,
        section="A",
        teacher_id=teacher.id,
        is_active=True,
    )
    db.add(classroom)
    db.commit()

    try:
        yield db, user, teacher, classroom
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def make_session(
    db,
    classroom_id,
    session_id,
    *,
    started_at=None,
    status="ACTIVE",
    ended_at=None,
):
    session = ClassroomSession(
        session_id=session_id,
        classroom_id=classroom_id,
        started_at=started_at or datetime.now(timezone.utc),
        ended_at=ended_at,
        duration_seconds=None,
        status=status,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_start_session_persists_active_session_with_timestamps(session_context):
    db, user, _, classroom = session_context

    result = start_classroom_session(
        classroom_id=classroom.id,
        current_user=user,
        db=db,
    )

    stored = (
        db.query(ClassroomSession)
        .filter(ClassroomSession.session_id == result["session"].session_id)
        .one()
    )
    assert result["session"].id == stored.id
    assert stored.classroom_id == classroom.id
    assert stored.started_at is not None
    assert stored.ended_at is None
    assert stored.duration_seconds is None
    assert stored.status == "ACTIVE"


def test_start_session_rejects_unknown_or_other_teachers_classroom(
    session_context,
):
    db, user, _, classroom = session_context

    with pytest.raises(HTTPException) as missing:
        start_classroom_session(
            classroom_id=999,
            current_user=user,
            db=db,
        )
    assert missing.value.status_code == 404

    other_user = User(
        id=2,
        username="other",
        email="other@example.test",
        password_hash="not-used",
        role="TEACHER",
        is_active=True,
    )
    db.add(other_user)
    db.flush()
    other_teacher = Teacher(
        user_id=other_user.id,
        teacher_id="T2",
        name="Other Teacher",
        department="Computing",
    )
    db.add(other_teacher)
    db.flush()
    other_classroom = Classroom(
        classroom_code="C2",
        name="Classroom 2",
        department="Computing",
        year=1,
        section="B",
        teacher_id=other_teacher.id,
        is_active=True,
    )
    db.add(other_classroom)
    db.commit()

    with pytest.raises(HTTPException) as forbidden:
        start_classroom_session(
            classroom_id=other_classroom.id,
            current_user=user,
            db=db,
        )
    assert forbidden.value.status_code == 404
    assert db.query(ClassroomSession).count() == 0
    assert classroom.id != other_classroom.id


def test_start_session_rejects_duplicate_active_session(session_context):
    db, user, _, classroom = session_context
    existing = make_session(db, classroom.id, "SESSION_ALREADY_ACTIVE")

    with pytest.raises(HTTPException) as error:
        start_classroom_session(
            classroom_id=classroom.id,
            current_user=user,
            db=db,
        )

    assert error.value.status_code == 409
    assert db.query(ClassroomSession).count() == 1
    assert db.query(ClassroomSession).one().id == existing.id


def test_start_session_rejects_non_teacher(session_context):
    db, user, _, classroom = session_context
    user.role = "ADMIN"

    with pytest.raises(HTTPException) as error:
        start_classroom_session(
            classroom_id=classroom.id,
            current_user=user,
            db=db,
        )

    assert error.value.status_code == 403


def test_active_endpoint_returns_current_record_and_404_when_inactive(
    session_context,
):
    db, user, _, classroom = session_context

    with pytest.raises(HTTPException) as inactive:
        get_active_classroom_session(
            classroom_id=classroom.id,
            current_user=user,
            db=db,
        )
    assert inactive.value.status_code == 404
    assert inactive.value.detail == "No active classroom session"

    active = make_session(db, classroom.id, "SESSION_ACTIVE")
    result = get_active_classroom_session(
        classroom_id=classroom.id,
        current_user=user,
        db=db,
    )
    assert result.id == active.id
    assert result.status == "ACTIVE"


def test_stop_session_persists_end_timestamp_status_and_duration(
    session_context,
):
    db, user, _, classroom = session_context
    started_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    active = make_session(
        db,
        classroom.id,
        "SESSION_STOP",
        started_at=started_at,
    )

    result = stop_classroom_session(
        classroom_id=classroom.id,
        session_id=active.session_id,
        current_user=user,
        db=db,
    )
    db.refresh(active)

    assert result["session"].status == "COMPLETED"
    assert active.status == "COMPLETED"
    assert active.ended_at is not None
    assert active.duration_seconds >= 180


def test_stop_session_rejects_unknown_wrong_class_and_stopped_session(
    session_context,
):
    db, user, _, classroom = session_context

    with pytest.raises(HTTPException) as missing:
        stop_classroom_session(
            classroom_id=classroom.id,
            session_id="MISSING",
            current_user=user,
            db=db,
        )
    assert missing.value.status_code == 404

    stopped = make_session(
        db,
        classroom.id,
        "SESSION_STOPPED",
        status="COMPLETED",
        ended_at=datetime.now(timezone.utc),
    )
    with pytest.raises(HTTPException) as conflict:
        stop_classroom_session(
            classroom_id=classroom.id,
            session_id=stopped.session_id,
            current_user=user,
            db=db,
        )
    assert conflict.value.status_code == 409

    with pytest.raises(HTTPException) as wrong_classroom:
        stop_classroom_session(
            classroom_id=classroom.id + 1,
            session_id=stopped.session_id,
            current_user=user,
            db=db,
        )
    assert wrong_classroom.value.status_code == 404


def test_history_is_teacher_scoped_newest_first_and_paginated(session_context):
    db, user, teacher, classroom = session_context
    older = make_session(
        db,
        classroom.id,
        "SESSION_OLDER",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="COMPLETED",
        ended_at=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
    )
    newer = make_session(
        db,
        classroom.id,
        "SESSION_NEWER",
        started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    other_classroom = Classroom(
        classroom_code="C2",
        name="Other Classroom",
        department="Computing",
        year=1,
        section="B",
        teacher_id=teacher.id + 1,
        is_active=True,
    )
    db.add(other_classroom)
    db.flush()
    make_session(db, other_classroom.id, "SESSION_OTHER")

    history = get_classroom_session_history(
        classroom_id=classroom.id,
        limit=1,
        offset=0,
        current_user=user,
        db=db,
    )

    assert [item.id for item in history] == [newer.id]

    next_page = get_classroom_session_history(
        classroom_id=classroom.id,
        limit=1,
        offset=1,
        current_user=user,
        db=db,
    )
    assert [item.id for item in next_page] == [older.id]


def test_endpoints_require_bearer_auth_and_document_history_pagination(
    session_context,
):
    schema = app.openapi()
    paths = schema["paths"]
    prefix = f"{API_VERSION.rstrip('/')}/classrooms/{{classroom_id}}/sessions"

    assert paths[prefix]["post"]["security"]
    assert paths[f"{prefix}/active"]["get"]["security"]
    assert paths[f"{prefix}/{{session_id}}/stop"]["post"]["security"]

    history = paths[prefix]["get"]
    params = {item["name"]: item for item in history["parameters"]}
    assert params["limit"]["schema"]["minimum"] == 1
    assert params["limit"]["schema"]["maximum"] == 100
    assert params["offset"]["schema"]["minimum"] == 0

    db, user, _, classroom = session_context
    user.role = "STUDENT"
    with pytest.raises(HTTPException) as forbidden:
        get_active_classroom_session(
            classroom_id=classroom.id,
            current_user=user,
            db=db,
        )
    assert forbidden.value.status_code == 403


def test_session_database_failure_is_sanitized():
    class BrokenSession:
        def query(self, *_args):
            raise OperationalError(
                "SELECT",
                {},
                RuntimeError("sensitive database details"),
            )

        def rollback(self):
            return None

        def rollback(self):
            return None

    teacher = User(
        id=1,
        username="teacher",
        email="teacher@example.test",
        password_hash="not-used",
        role="TEACHER",
        is_active=True,
    )

    with pytest.raises(HTTPException) as error:
        get_active_classroom_session(
            classroom_id=1,
            current_user=teacher,
            db=BrokenSession(),
        )

    assert error.value.status_code == 503
    assert "sensitive database details" not in error.value.detail
