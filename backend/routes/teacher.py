from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.schemas.teacher import (
    TeacherCreateRequest,
    TeacherResponse,
)


router = APIRouter(
    prefix="/teachers",
    tags=["Teachers"],
)


@router.post(
    "/profile",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_teacher_profile(
    request: TeacherCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create a teacher profile",
        )

    existing_profile = (
        db.query(Teacher)
        .filter(Teacher.user_id == current_user.id)
        .first()
    )

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Teacher profile already exists",
        )

    existing_teacher_id = (
        db.query(Teacher)
        .filter(Teacher.teacher_id == request.teacher_id)
        .first()
    )

    if existing_teacher_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Teacher ID already exists",
        )

    teacher = Teacher(
        user_id=current_user.id,
        teacher_id=request.teacher_id,
        name=request.name,
        department=request.department,
        designation=request.designation,
    )

    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    return teacher


@router.get(
    "/me",
    response_model=TeacherResponse,
)
def get_teacher_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access a teacher profile",
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

    return teacher