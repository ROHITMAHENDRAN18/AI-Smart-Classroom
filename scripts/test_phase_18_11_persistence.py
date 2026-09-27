"""Round-trip test for Phase 18.11 persistence fields.

Creates uniquely named temporary records, verifies them through a fresh
session, then removes test data even if an assertion fails.
"""

from uuid import uuid4

from ai.database.classroom_database import ClassroomDatabase
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord
from backend.models.classroom_session import ClassroomSession


def main():
    token = uuid4().hex
    session_id = f"PHASE18_11_TEST_{token}"
    student_id = f"PHASE18_11_STUDENT_{token}"
    track_id = 980000 + int(token[:6], 16) % 10000
    database = ClassroomDatabase()

    try:
        database.start_session(session_id=session_id)
        database.record_attendance(
            session_id=session_id,
            student_id=student_id,
            status="PRESENT",
            confidence=0.91,
        )
        written = database.record_attention(
            session_id=session_id,
            student_id=student_id,
            track_id=track_id,
            attention_state="UNKNOWN",
            confidence=None,
            attention_score=82.34,
            fusion_state="ATTENTIVE",
            fusion_score=0.8234,
            fusion_confidence=0.30,
            temporal_state="ATTENTIVE",
            temporal_score=0.8234,
            temporal_confidence=0.2475,
            temporal_stable=True,
        )

        session = database.get_session()
        try:
            persisted = (
                session.query(AttentionRecord)
                .filter_by(session_id=session_id, student_id=student_id)
                .one()
            )
            attendance = (
                session.query(AttendanceRecord)
                .filter_by(session_id=session_id, student_id=student_id)
                .one()
            )
            assert persisted.id == written.id
            assert attendance.status == "PRESENT"
            assert persisted.track_id == track_id
            assert persisted.attention_state == "UNKNOWN"
            assert persisted.attention_score == 82.34
            assert persisted.fusion_state == "ATTENTIVE"
            assert persisted.fusion_score == 0.8234
            assert persisted.fusion_confidence == 0.30
            assert persisted.temporal_state == "ATTENTIVE"
            assert persisted.temporal_score == 0.8234
            assert persisted.temporal_confidence == 0.2475
            assert persisted.temporal_stable is True
        finally:
            session.close()

        database.finish_session(session_id=session_id)
        print("Phase 18.11 session, attendance, and attention round trip passed.")
    finally:
        cleanup = database.get_session()
        try:
            cleanup.query(AttentionRecord).filter_by(session_id=session_id).delete(
                synchronize_session=False
            )
            cleanup.query(AttendanceRecord).filter_by(session_id=session_id).delete(
                synchronize_session=False
            )
            cleanup.query(ClassroomSession).filter_by(session_id=session_id).delete(
                synchronize_session=False
            )
            cleanup.commit()
        except Exception:
            cleanup.rollback()
            raise
        finally:
            cleanup.close()


if __name__ == "__main__":
    main()
