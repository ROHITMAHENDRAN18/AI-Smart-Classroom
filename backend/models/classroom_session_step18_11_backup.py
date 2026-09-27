from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.sql import func

from backend.database.base import Base


class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    session_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_seconds = Column(
        Integer,
        nullable=True,
    )

    status = Column(
        String,
        nullable=False,
        default="ACTIVE",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )