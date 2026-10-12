from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.database.base import Base
from backend.models.attention_record import AttentionRecord
from backend.models.classroom import Classroom
from backend.models.classroom_session import ClassroomSession
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.routes.alerts import list_alerts
from configs.settings import API_VERSION


@pytest.fixture
def alerts_context():
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

    try:
        yield db, user
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def add_teacher_session(db, *, user_id, session_id, student_id):
    user = User(
        id=user_id,
        username=f"teacher-{user_id}",
        email=f"teacher-{user_id}@example.test",
        password_hash="not-used",
        role="TEACHER",
        is_active=True,
    )
    db.add(user)
    db.flush()

    teacher = Teacher(
        user_id=user.id,
        teacher_id=f"T{user_id}",
        name=f"Teacher {user_id}",
        department="Computing",
    )
    db.add(teacher)
    db.flush()

    classroom = Classroom(
        classroom_code=f"C{user_id}",
        name=f"Classroom {user_id}",
        department="Computing",
        year=1,
        section="A",
        teacher_id=teacher.id,
        is_active=True,
    )
    db.add(classroom)
    db.flush()

    classroom_session = ClassroomSession(
        session_id=session_id,
        classroom_id=classroom.id,
        started_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        status="COMPLETED",
    )
    db.add(classroom_session)
    db.flush()

    record = AttentionRecord(
        session_id=session_id,
        student_id=student_id,
        track_id=7,
        attention_state="NOT ATTENTIVE",
        confidence=0.8,
        recorded_at=datetime(2026, 10, 1, 10, tzinfo=timezone.utc),
    )
    db.add(record)
    db.flush()

    return user, record


def call_alerts(db, user, *, limit=50, offset=0, session_id=None):
    return list_alerts(
        limit=limit,
        offset=offset,
        session_id=session_id,
        current_user=user,
        db=db,
    )


def test_alerts_returns_persisted_not_attentive_records(alerts_context):
    db, user = alerts_context
    _, record = add_teacher_session(
        db,
        user_id=user.id,
        session_id="SESSION_ALERTS_1",
        student_id="STUDENT_1",
    )
    db.add(
        AttentionRecord(
            session_id="SESSION_ALERTS_1",
            student_id="STUDENT_1",
            attention_state="ATTENTIVE",
            recorded_at=datetime(2026, 10, 1, 11, tzinfo=timezone.utc),
        )
    )
    db.commit()

    alerts = call_alerts(db, user)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_id == f"attention-{record.id}"
    assert alert.alert_type == "NOT ATTENTIVE"
    assert alert.message == "Student STUDENT_1 was recorded as not attentive."
    assert alert.severity is None
    assert alert.session_id == "SESSION_ALERTS_1"
    assert alert.student_id == "STUDENT_1"
    assert alert.track_id == 7
    assert alert.timestamp == datetime(2026, 10, 1, 10)


def test_alerts_returns_empty_list_when_no_matching_records(alerts_context):
    db, user = alerts_context
    add_teacher_session(
        db,
        user_id=user.id,
        session_id="SESSION_ALERTS_EMPTY",
        student_id="STUDENT_1",
    )
    db.query(AttentionRecord).delete()
    db.commit()

    assert call_alerts(db, user) == []


def test_alerts_are_limited_to_the_authenticated_teachers_classrooms(
    alerts_context,
):
    db, user = alerts_context
    add_teacher_session(
        db,
        user_id=user.id,
        session_id="SESSION_OWN",
        student_id="OWN_STUDENT",
    )
    add_teacher_session(
        db,
        user_id=2,
        session_id="SESSION_OTHER",
        student_id="OTHER_STUDENT",
    )
    db.commit()

    alerts = call_alerts(db, user)

    assert [alert.student_id for alert in alerts] == ["OWN_STUDENT"]


def test_alerts_support_session_filter_and_pagination(alerts_context):
    db, user = alerts_context
    add_teacher_session(
        db,
        user_id=user.id,
        session_id="SESSION_FILTERED",
        student_id="STUDENT_1",
    )
    db.commit()

    assert call_alerts(db, user, session_id="NO_SUCH_SESSION") == []
    assert call_alerts(db, user, limit=1, offset=1) == []


def test_alerts_require_teacher_or_admin_and_openapi_documents_contract(
    alerts_context,
):
    db, user = alerts_context
    user.role = "STUDENT"

    with pytest.raises(HTTPException) as error:
        call_alerts(db, user)

    assert error.value.status_code == 403

    schema = app.openapi()
    operation = schema["paths"][f"{API_VERSION.rstrip('/')}/alerts"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert operation["security"]
    assert parameters["limit"]["schema"]["maximum"] == 100
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["offset"]["schema"]["minimum"] == 0
    assert "session_id" in parameters
    assert operation["responses"]["200"]["content"]["application/json"]

    response_schema = schema["components"]["schemas"]["AlertResponse"]
    assert set(response_schema["required"]) == {
        "alert_id",
        "alert_type",
        "message",
        "severity",
        "timestamp",
        "session_id",
        "student_id",
        "track_id",
    }
    assert response_schema["properties"]["alert_id"]["type"] == "string"
    assert response_schema["properties"]["timestamp"]["format"] == "date-time"
    assert response_schema["properties"]["severity"]["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]


def test_alert_database_failure_returns_sanitized_service_error():
    class BrokenSession:
        def query(self, *_args):
            raise OperationalError(
                "SELECT",
                {},
                RuntimeError("sensitive database details"),
            )

    admin = User(
        id=9,
        username="admin",
        email="admin@example.test",
        password_hash="not-used",
        role="ADMIN",
        is_active=True,
    )

    with pytest.raises(HTTPException) as error:
        call_alerts(BrokenSession(), admin)

    assert error.value.status_code == 503
    assert error.value.detail == "Alert data is temporarily unavailable."
    assert "sensitive database details" not in error.value.detail
