from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.student import Student
from backend.models.user import User
from backend.schemas.student import (
    StudentCreateRequest,
    StudentResponse,
    StudentUpdateRequest,
)


router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


def require_teacher_or_admin(
    current_user: User,
):
    if current_user.role not in {"TEACHER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can manage students",
        )


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student(
    request: StudentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_teacher_or_admin(current_user)

    existing_student = (
        db.query(Student)
        .filter(Student.student_id == request.student_id)
        .first()
    )

    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student ID already exists",
        )

    if request.email is not None:
        existing_email = (
            db.query(Student)
            .filter(Student.email == str(request.email))
            .first()
        )

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Student email already exists",
            )

    student = Student(
        student_id=request.student_id,
        name=request.name,
        department=request.department,
        year=request.year,
        section=request.section,
        email=str(request.email) if request.email else None,
        face_registered=False,
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


@router.get(
    "",
    response_model=list[StudentResponse],
)
def get_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_teacher_or_admin(current_user)

    students = (
        db.query(Student)
        .order_by(Student.id)
        .all()
    )

    return students


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
def get_student(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_teacher_or_admin(current_user)

    student = (
        db.query(Student)
        .filter(Student.student_id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    return student


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
)
def update_student(
    student_id: str,
    request: StudentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_teacher_or_admin(current_user)

    student = (
        db.query(Student)
        .filter(Student.student_id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    update_data = request.model_dump(
        exclude_unset=True,
    )

    if "email" in update_data:
        email = update_data["email"]

        if email is not None:
            existing_email = (
                db.query(Student)
                .filter(
                    Student.email == str(email),
                    Student.student_id != student_id,
                )
                .first()
            )

            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Student email already exists",
                )

            update_data["email"] = str(email)

    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    return student


@router.delete(
    "/{student_id}",
    response_model=StudentResponse,
)
def deactivate_student(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_teacher_or_admin(current_user)

    student = (
        db.query(Student)
        .filter(Student.student_id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    student.face_registered = False

    db.commit()
    db.refresh(student)

    return student
