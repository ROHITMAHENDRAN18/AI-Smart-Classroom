from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.models.classroom_session import ClassroomSession
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord


class ClassroomDatabase:

    def __init__(self):
        print("============================================================")
        print("Loading Classroom Database...")
        print("============================================================")
        print("Classroom Database Loaded Successfully.")
        print("============================================================")

    def get_session(self) -> Session:
        return SessionLocal()

    def start_session(
        self,
        session_id: str,
        started_at: datetime | None = None,
    ):
        db = self.get_session()

        try:
            existing_session = (
                db.query(ClassroomSession)
                .filter(
                    ClassroomSession.session_id == session_id
                )
                .first()
            )

            if existing_session:
                return existing_session

            if started_at is None:
                started_at = datetime.now(timezone.utc)

            classroom_session = ClassroomSession(
                session_id=session_id,
                started_at=started_at,
                status="ACTIVE",
            )

            db.add(classroom_session)
            db.commit()
            db.refresh(classroom_session)

            print("============================================================")
            print("DATABASE CLASSROOM SESSION STARTED")
            print("============================================================")
            print(f"Session ID : {classroom_session.session_id}")
            print(f"Started At : {classroom_session.started_at.isoformat()}")
            print("============================================================")

            return classroom_session

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def record_attendance(
        self,
        session_id: str,
        student_id: str,
        status: str = "PRESENT",
        confidence: float | None = None,
    ):
        db = self.get_session()

        try:
            attendance = (
                db.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.student_id == student_id,
                )
                .first()
            )

            if attendance is None:
                attendance = AttendanceRecord(
                    session_id=session_id,
                    student_id=student_id,
                    status=status,
                    confidence=confidence,
                )

                db.add(attendance)

            else:
                attendance.status = status

                if confidence is not None:
                    attendance.confidence = confidence

            db.commit()
            db.refresh(attendance)

            return attendance

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def record_attention(
        self,
        session_id: str,
        student_id: str,
        track_id: int | None,
        attention_state: str,
        confidence: float | None = None,
    ):
        db = self.get_session()

        try:
            attention = AttentionRecord(
                session_id=session_id,
                student_id=student_id,
                track_id=track_id,
                attention_state=attention_state,
                confidence=confidence,
            )

            db.add(attention)
            db.commit()
            db.refresh(attention)

            return attention

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def finish_session(
        self,
        session_id: str,
        ended_at: datetime | None = None,
        duration_seconds: int | None = None,
        status: str = "COMPLETED",
    ):
        db = self.get_session()

        try:
            classroom_session = (
                db.query(ClassroomSession)
                .filter(
                    ClassroomSession.session_id == session_id
                )
                .first()
            )

            if classroom_session is None:
                return None

            if ended_at is None:
                ended_at = datetime.now(timezone.utc)

            classroom_session.ended_at = ended_at
            classroom_session.duration_seconds = duration_seconds
            classroom_session.status = status

            db.commit()
            db.refresh(classroom_session)

            return classroom_session

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()