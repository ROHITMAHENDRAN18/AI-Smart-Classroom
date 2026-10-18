from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.models.attention_record import AttentionRecord
from backend.models.attendance_record import AttendanceRecord
from backend.models.classroom import Classroom
from backend.models.classroom_member import ClassroomMember
from backend.models.classroom_session import ClassroomSession
from backend.models.student import Student
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.services.history_service import (
    get_session_summary,
    summarize_attention_observations,
)


@pytest.fixture
def history_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    user = User(
        username="history-teacher",
        email="history-teacher@example.test",
        password_hash="unused",
        role="TEACHER",
    )
    db.add(user)
    db.flush()
    teacher = Teacher(
        user_id=user.id,
        teacher_id="HISTORY-T1",
        name="History Teacher",
        department="Computing",
    )
    db.add(teacher)
    db.flush()
    classroom = Classroom(
        classroom_code="HISTORY-C1",
        name="History Classroom",
        department="Computing",
        year=1,
        section="A",
        teacher_id=teacher.id,
    )
    db.add(classroom)
    db.flush()

    for session_id in ("selected", "other", "empty"):
        db.add(
            ClassroomSession(
                session_id=session_id,
                classroom_id=classroom.id,
                started_at=datetime.now(timezone.utc),
                status="COMPLETED",
            )
        )
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_supported_states_and_percentages_use_valid_denominator():
    records = [
        SimpleNamespace(attention_state=state)
        for state in ("LISTENING", "SLEEPING", "LOOKING_AWAY", "UNKNOWN")
    ]

    summary = summarize_attention_observations(records)

    assert summary["attention_records"] == 4
    assert summary["valid_attention_records"] == 4
    assert summary["attentive_count"] == 1
    assert summary["not_attentive_count"] == 2
    assert summary["unknown_count"] == 1
    assert summary["attentive_percentage"] == 25
    assert summary["not_attentive_percentage"] == 50
    assert summary["unknown_percentage"] == 25


def test_mixed_legacy_null_and_unsupported_states_are_reported():
    records = [
        SimpleNamespace(attention_state=state)
        for state in (
            "LISTENING",
            "SLEEPING",
            "UNKNOWN",
            "ATTENTIVE",
            "NOT_ATTENTIVE",
            "PARTIAL",
            None,
            "FUTURE_STATE",
        )
    ]

    summary = summarize_attention_observations(records)

    assert summary["attention_records"] == 8
    assert summary["valid_attention_records"] == 3
    assert summary["data_quality_records"] == 5
    assert summary["attentive_count"] + summary["not_attentive_count"] + summary["unknown_count"] == 3
    assert summary["data_quality_state_counts"] == {
        "LEGACY: ATTENTIVE": 1,
        "LEGACY: NOT ATTENTIVE": 1,
        "LEGACY: PARTIAL": 1,
        "NULL": 1,
        "FUTURE_STATE": 1,
    }


def test_empty_session_has_zero_counts_and_percentages(history_db):
    summary = get_session_summary(history_db, "empty")

    assert summary["statistics"]["attention_records"] == 0
    assert summary["statistics"]["valid_attention_records"] == 0
    assert summary["statistics"]["data_quality_records"] == 0
    assert summary["statistics"]["attentive_percentage"] == 0
    assert summary["statistics"]["not_attentive_percentage"] == 0
    assert summary["statistics"]["unknown_percentage"] == 0


def test_summary_filters_observations_to_selected_session(history_db):
    session = history_db.query(ClassroomSession).filter_by(
        session_id="selected"
    ).one()
    history_db.add(
        Student(
            student_id="S1",
            name="Verified Student",
            department="Computing",
            year=1,
            section="A",
            face_registered=True,
        )
    )
    history_db.flush()
    history_db.add(
        ClassroomMember(
            classroom_id=session.classroom_id,
            student_id="S1",
            joined_at=session.started_at,
            is_active=True,
        )
    )
    timestamp = datetime.now(timezone.utc)
    for session_id, state in (
        ("selected", "LISTENING"),
        ("selected", "SLEEPING"),
        ("selected", "LOOKING_AWAY"),
        ("selected", "UNKNOWN"),
        ("other", "LISTENING"),
    ):
        history_db.add(
            AttentionRecord(
                session_id=session_id,
                student_id="S1",
                attention_state=state,
                temporal_state="A_DIFFERENT_STATE",
                recorded_at=timestamp,
            )
        )
    history_db.commit()

    summary = get_session_summary(history_db, "selected")
    stats = summary["statistics"]

    assert len(summary["attention"]) == 4
    assert {record.session_id for record in summary["attention"]} == {"selected"}
    assert stats["attention_records"] == 4
    assert stats["valid_attention_records"] == 4
    assert stats["attentive_count"] == 1
    assert stats["not_attentive_count"] == 2
    assert stats["unknown_count"] == 1
    assert stats["attentive_percentage"] + stats["not_attentive_percentage"] + stats["unknown_percentage"] == 100
    assert stats["unassigned_attention_records"] == 0


def test_summary_excludes_unassigned_rows_but_keeps_verified_unknown(history_db):
    session = history_db.query(ClassroomSession).filter_by(
        session_id="selected"
    ).one()
    eligible = [
        Student(
            student_id=student_id,
            name=student_id,
            department="Computing",
            year=1,
            section="A",
            face_registered=True,
        )
        for student_id in ("VERIFIED_A", "VERIFIED_B", "REGISTERED_NO_MEMBER")
    ]
    unregistered = Student(
        student_id="UNREGISTERED",
        name="Unregistered Student",
        department="Computing",
        year=1,
        section="A",
        face_registered=False,
    )
    history_db.add_all([*eligible, unregistered])
    history_db.flush()
    history_db.add_all(
        [
            ClassroomMember(
                classroom_id=session.classroom_id,
                student_id=student_id,
                joined_at=session.started_at,
                is_active=True,
            )
            for student_id in ("VERIFIED_A", "VERIFIED_B", "UNREGISTERED")
        ]
    )
    timestamp = datetime.now(timezone.utc)
    states_by_student = {
        "VERIFIED_A": ("LISTENING", "UNKNOWN"),
        "VERIFIED_B": ("SLEEPING", "LOOKING_AWAY"),
        "UNREGISTERED": ("UNKNOWN",),
        "REGISTERED_NO_MEMBER": ("UNKNOWN",),
        "MISSING_STUDENT": ("UNKNOWN",),
    }
    history_db.add_all(
        AttentionRecord(
            session_id="selected",
            student_id=student_id,
            attention_state=state,
            recorded_at=timestamp,
        )
        for student_id, states in states_by_student.items()
        for state in states
    )
    history_db.add(
        AttendanceRecord(
            session_id="selected",
            student_id="VERIFIED_A",
            status="PRESENT",
        )
    )
    history_db.commit()

    summary = get_session_summary(history_db, "selected")
    stats = summary["statistics"]

    assert len(summary["attention"]) == 4
    assert {record.student_id for record in summary["attention"]} == {
        "VERIFIED_A",
        "VERIFIED_B",
    }
    assert stats["attention_records"] == 4
    assert stats["attendance_records"] == 1
    assert stats["present_students"] == 1
    assert stats["unassigned_attention_records"] == 3
    assert stats["attentive_count"] == 1
    assert stats["not_attentive_count"] == 2
    assert stats["unknown_count"] == 1
    assert stats["valid_attention_records"] == 4
    assert stats["attentive_percentage"] == 25
    assert stats["not_attentive_percentage"] == 50
    assert stats["unknown_percentage"] == 25


def test_session_attendance_counts_use_active_roster_and_persisted_statuses(history_db):
    classroom_id = history_db.query(ClassroomSession).filter_by(
        session_id="selected"
    ).one().classroom_id
    students = [
        Student(
            student_id=f"ROSTER_{index}",
            name=f"Roster Student {index}",
            department="Computing",
            year=1,
            section="A",
        )
        for index in range(5)
    ]
    history_db.add_all(students)
    history_db.flush()
    history_db.add_all(
        [
            ClassroomMember(
                classroom_id=classroom_id,
                student_id=student.student_id,
                is_active=index < 4,
            )
            for index, student in enumerate(students)
        ]
    )
    history_db.add_all(
        [
            AttendanceRecord(
                session_id="selected",
                student_id="ROSTER_0",
                status="PRESENT",
            ),
            AttendanceRecord(
                session_id="selected",
                student_id="ROSTER_1",
                status="ABSENT",
            ),
            AttendanceRecord(
                session_id="selected",
                student_id="ROSTER_2",
                status="UNKNOWN",
            ),
            AttendanceRecord(
                session_id="selected",
                student_id="ROSTER_3",
                status="LEGACY_STATUS",
            ),
            # A record from another session must not affect this session.
            AttendanceRecord(
                session_id="other",
                student_id="ROSTER_3",
                status="PRESENT",
            ),
            # A record for a no-longer-active member is not in the live roster.
            AttendanceRecord(
                session_id="selected",
                student_id="ROSTER_4",
                status="PRESENT",
            ),
        ]
    )
    history_db.commit()

    stats = get_session_summary(history_db, "selected")["statistics"]

    assert stats["enrolled_students"] == 4
    assert stats["present_students"] == 1
    assert stats["absent_students"] == 1
    assert stats["unknown_attendance_students"] == 1
    assert stats["attendance_data_quality_students"] == 1
    assert stats["unmarked_students"] == 0
    assert (
        stats["present_students"]
        + stats["absent_students"]
        + stats["unknown_attendance_students"]
        + stats["attendance_data_quality_students"]
        + stats["unmarked_students"]
        == stats["enrolled_students"]
    )


def test_session_roster_members_without_records_are_unmarked_not_absent(history_db):
    classroom_id = history_db.query(ClassroomSession).filter_by(
        session_id="empty"
    ).one().classroom_id
    student = Student(
        student_id="ROSTER_UNMARKED",
        name="Unmarked Student",
        department="Computing",
        year=1,
        section="A",
    )
    history_db.add(student)
    history_db.flush()
    history_db.add(
        ClassroomMember(
            classroom_id=classroom_id,
            student_id=student.student_id,
            is_active=True,
        )
    )
    history_db.commit()

    stats = get_session_summary(history_db, "empty")["statistics"]

    assert stats["enrolled_students"] == 1
    assert stats["present_students"] == 0
    assert stats["absent_students"] == 0
    assert stats["unmarked_students"] == 1
