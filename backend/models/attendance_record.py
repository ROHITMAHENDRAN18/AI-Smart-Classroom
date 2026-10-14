from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import func

from backend.database.base import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_attendance_session_student",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    session_id = Column(
        String,
        nullable=False,
        index=True,
    )

    student_id = Column(
        String,
        nullable=False,
        index=True,
    )

    status = Column(
        String,
        nullable=False,
        default="PRESENT",
    )

    confidence = Column(
        Float,
        nullable=True,
    )

    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
