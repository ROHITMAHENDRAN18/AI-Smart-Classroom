from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class FrameInferenceSummary(Base):
    """Bounded latest-result summary; classroom image bytes are never stored."""

    __tablename__ = "frame_inference_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("classroom_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    classroom_id: Mapped[int] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    latest_frame_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    latest_processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    frame_width: Mapped[int] = mapped_column(Integer, nullable=False)
    frame_height: Mapped[int] = mapped_column(Integer, nullable=False)
    detection_count: Mapped[int] = mapped_column(Integer, nullable=False)
    inference_duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    detections: Mapped[list[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    face_detections: Mapped[list[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    face_detection_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="error"
    )
    frames_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
