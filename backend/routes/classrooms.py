from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom import Classroom
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.schemas.classroom import (
    ClassroomCreateRequest,
    ClassroomResponse,
    ClassroomUpdateRequest,
)


router = APIRouter(
    prefix="/classrooms",
    tags=["Classrooms"],
)


def get_current_teacher(
    current_user: User,
    db: Session,
) -> Teacher:
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can manage classrooms",
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


@router.post(
    "",
    response_model=ClassroomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_classroom(
    request: ClassroomCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    existing_classroom = (
        db.query(Classroom)
        .filter(
            Classroom.classroom_code
            == request.classroom_code
        )
        .first()
    )

    if existing_classroom:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Classroom code already exists",
        )

    classroom = Classroom(
        classroom_code=request.classroom_code,
        name=request.name,
        department=request.department,
        year=request.year,
        section=request.section,
        teacher_id=teacher.id,
        is_active=True,
    )

    db.add(classroom)
    db.commit()
    db.refresh(classroom)

    return classroom


@router.get(
    "",
    response_model=list[ClassroomResponse],
)
def get_my_classrooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    classrooms = (
        db.query(Classroom)
        .filter(
            Classroom.teacher_id == teacher.id,
        )
        .order_by(Classroom.id)
        .all()
    )

    return classrooms


@router.get(
    "/{classroom_id}",
    response_model=ClassroomResponse,
)
def get_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == classroom_id,
            Classroom.teacher_id == teacher.id,
        )
        .first()
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )

    return classroom


@router.put(
    "/{classroom_id}",
    response_model=ClassroomResponse,
)
def update_classroom(
    classroom_id: int,
    request: ClassroomUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == classroom_id,
            Classroom.teacher_id == teacher.id,
        )
        .first()
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )

    update_data = request.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(
            classroom,
            field,
            value,
        )

    db.commit()
    db.refresh(classroom)

    return classroom


@router.delete(
    "/{classroom_id}",
    response_model=ClassroomResponse,
)
def deactivate_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == classroom_id,
            Classroom.teacher_id == teacher.id,
        )
        .first()
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )

    classroom.is_active = False

    db.commit()
    db.refresh(classroom)

    return classroom