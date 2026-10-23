from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.classroom import Classroom
from backend.models.teacher import Teacher
from backend.models.user import User


def get_owned_classroom_ids(
    current_user: User,
    db: Session,
) -> list[int] | None:
    if current_user.role == "ADMIN":
        return None

    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can access classroom data",
        )

    teacher = (
        db.query(Teacher)
        .filter(Teacher.user_id == current_user.id)
        .first()
    )
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found",
        )

    return [
        classroom_id
        for (classroom_id,) in (
            db.query(Classroom.id)
            .order_by(Classroom.id)
            .all()
        )
    ]


def require_classroom_access(
    classroom_id: int,
    current_user: User,
    db: Session,
    *,
    require_active: bool = False,
) -> Classroom:
    if current_user.role not in ("ADMIN", "TEACHER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can access classroom data",
        )

    query = db.query(Classroom).filter(Classroom.id == classroom_id)

    classroom = query.first()
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )
    if require_active and not classroom.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Classroom is inactive",
        )

    return classroom
