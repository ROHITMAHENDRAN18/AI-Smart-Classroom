from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.models.attendance_record import AttendanceRecord
from backend.models.classroom import Classroom
from backend.models.classroom_member import ClassroomMember
from backend.models.classroom_session import ClassroomSession
from backend.models.student import Student
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.routes.classroom_data import classroom_attendance
from backend.routes.students import get_student, get_students
from backend.services.analytics_service import get_total_sessions


@pytest.fixture
def classroom_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    user = User(
        username="teacher",
        email="teacher@example.test",
        password_hash="unused",
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
    db.flush()
    session = ClassroomSession(
        session_id="SESSION_1",
        classroom_id=classroom.id,
        started_at=datetime(2025, 1, 2, 9, tzinfo=timezone.utc),
        status="COMPLETED",
    )
    db.add(session)
    other_user = User(
        username="other",
        email="other@example.test",
        password_hash="unused",
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
    db.flush()
    db.add(
        ClassroomSession(
            session_id="SESSION_OTHER",
            classroom_id=other_classroom.id,
            started_at=datetime(2025, 1, 2, 9, tzinfo=timezone.utc),
            status="COMPLETED",
        )
    )
    student = Student(
        student_id="S1",
        name="Student One",
        department="Computing",
        year=1,
        section="A",
        face_registered=False,
    )
    other_student = Student(
        student_id="S2",
        name="Student Two",
        department="Computing",
        year=1,
        section="B",
        face_registered=False,
    )
    db.add_all([student, other_student])
    db.flush()
    db.add_all(
        [
            ClassroomMember(
                classroom_id=classroom.id,
                student_id=student.student_id,
                is_active=True,
            ),
            ClassroomMember(
                classroom_id=other_classroom.id,
                student_id=other_student.student_id,
                is_active=True,
            ),
        ]
    )
    db.add_all(
        [
            AttendanceRecord(
                session_id=session.session_id,
                student_id=f"S{index}",
                status=state,
                recorded_at=datetime(2025, 1, 2, 10 + index, tzinfo=timezone.utc),
            )
            for index, state in enumerate(("PRESENT", "ABSENT", "UNKNOWN"))
        ]
    )
    db.add(
        AttendanceRecord(
            session_id=session.session_id,
            student_id="S4",
            status="PRESENT",
            recorded_at=datetime(2025, 1, 3, 10, tzinfo=timezone.utc),
        )
    )
    db.commit()
    try:
        yield db, user, classroom, other_classroom
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_attendance_summary_uses_scoped_date_and_pagination(classroom_context):
    db, user, classroom, _ = classroom_context

    result = classroom_attendance(
        classroom_id=classroom.id,
        date_filter=None,
        from_date=datetime(2025, 1, 2).date(),
        to_date=datetime(2025, 1, 2).date(),
        session_id="SESSION_1",
        limit=2,
        offset=0,
        current_user=user,
        db=db,
    )

    assert result.total_records == 3
    assert result.present_count == 1
    assert result.absent_count == 1
    assert result.unknown_count == 1
    assert result.attendance_rate == 50
    assert len(result.records) == 2
    assert result.daily_trend[0].total_records == 3


def test_attendance_pagination_does_not_change_totals(classroom_context):
    db, user, classroom, _ = classroom_context

    result = classroom_attendance(
        classroom_id=classroom.id,
        date_filter=None,
        from_date=datetime(2025, 1, 2).date(),
        to_date=datetime(2025, 1, 3).date(),
        session_id=None,
        limit=1,
        offset=3,
        current_user=user,
        db=db,
    )

    assert result.total_records == 4
    assert result.present_count == 2
    assert result.absent_count == 1
    assert result.unknown_count == 1
    assert result.attendance_rate == pytest.approx(66.67)
    assert len(result.records) == 1


def test_empty_attendance_is_successful_with_undefined_rate(classroom_context):
    db, user, classroom, _ = classroom_context

    result = classroom_attendance(
        classroom_id=classroom.id,
        date_filter=None,
        from_date=datetime(2025, 2, 1).date(),
        to_date=datetime(2025, 2, 1).date(),
        session_id=None,
        limit=50,
        offset=0,
        current_user=user,
        db=db,
    )

    assert result.total_records == 0
    assert result.records == []
    assert result.daily_trend == []
    assert result.attendance_rate is None


def test_attendance_rejects_foreign_classroom_and_invalid_date_range(classroom_context):
    db, user, classroom, other_classroom = classroom_context
    with pytest.raises(HTTPException) as forbidden:
        classroom_attendance(
            classroom_id=other_classroom.id,
            date_filter=None,
            from_date=datetime(2025, 1, 2).date(),
            to_date=datetime(2025, 1, 2).date(),
            session_id=None,
            limit=50,
            offset=0,
            current_user=user,
            db=db,
        )
    assert forbidden.value.status_code == 404

    with pytest.raises(HTTPException) as invalid:
        classroom_attendance(
            classroom_id=classroom.id,
            date_filter=None,
            from_date=datetime(2025, 1, 3).date(),
            to_date=datetime(2025, 1, 2).date(),
            session_id=None,
            limit=50,
            offset=0,
            current_user=user,
            db=db,
        )
    assert invalid.value.status_code == 422


def test_attendance_requires_both_explicit_range_dates(classroom_context):
    db, user, classroom, _ = classroom_context
    with pytest.raises(HTTPException) as invalid:
        classroom_attendance(
            classroom_id=classroom.id,
            date_filter=None,
            from_date=datetime(2025, 1, 2).date(),
            to_date=None,
            session_id=None,
            limit=50,
            offset=0,
            current_user=user,
            db=db,
        )
    assert invalid.value.status_code == 422


def test_session_analytics_count_is_limited_to_authorized_classrooms(classroom_context):
    db, _, classroom, other_classroom = classroom_context

    assert get_total_sessions(db, [classroom.id]) == 1
    assert get_total_sessions(db, [other_classroom.id]) == 1
    assert get_total_sessions(db, []) == 0
    assert get_total_sessions(db) == 2


def test_students_are_limited_to_owned_classroom(classroom_context):
    db, user, classroom, _ = classroom_context

    students = get_students(
        classroom_id=classroom.id,
        current_user=user,
        db=db,
    )

    assert [student["student_id"] for student in students] == ["S1"]
    assert students[0]["classroom_is_active"] is True
    assert get_student("S1", current_user=user, db=db).student_id == "S1"
    with pytest.raises(HTTPException) as forbidden:
        get_student("S2", current_user=user, db=db)
    assert forbidden.value.status_code == 404
