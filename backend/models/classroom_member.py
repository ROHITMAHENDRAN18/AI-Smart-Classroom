from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class ClassroomMember(Base):
    __tablename__ = "classroom_members"

    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "student_id",
            name="uq_classroom_student",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    classroom_id: Mapped[int] = mapped_column(
        ForeignKey(
            "classrooms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id: Mapped[str] = mapped_column(
        ForeignKey(
            "students.student_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )