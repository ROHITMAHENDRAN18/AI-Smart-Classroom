from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy.sql import func

from backend.database.base import Base


class AttentionRecord(Base):
    __tablename__ = "attention_records"

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

    track_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    attention_state = Column(
        String,
        nullable=False,
    )

    attention_score = Column(
        Float,
        nullable=True,
    )

    fusion_state = Column(
        String(32),
        nullable=True,
    )

    fusion_score = Column(
        Float,
        nullable=True,
    )

    fusion_confidence = Column(
        Float,
        nullable=True,
    )

    temporal_state = Column(
        String(32),
        nullable=True,
    )

    temporal_score = Column(
        Float,
        nullable=True,
    )

    temporal_confidence = Column(
        Float,
        nullable=True,
    )

    temporal_stable = Column(
        Boolean,
        nullable=True,
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