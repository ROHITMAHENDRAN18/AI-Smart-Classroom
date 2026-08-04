from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.schemas.student import (
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from backend.services.student_service import (
    create_student,
    get_students,
    get_student_by_id,
    update_student,
    delete_student,
)

router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


@router.post(
    "/",
    response_model=StudentResponse,
)
def add_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
):
    return create_student(db, student)


@router.get(
    "/",
    response_model=list[StudentResponse],
)
def list_students(
    db: Session = Depends(get_db),
):
    return get_students(db)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return student


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
)
def update_student_route(
    student_id: int,
    student: StudentUpdate,
    db: Session = Depends(get_db),
):
    updated_student = update_student(
        db,
        student_id,
        student,
    )

    if not updated_student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return updated_student


@router.delete(
    "/{student_id}",
)
def delete_student_route(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = delete_student(db, student_id)

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return {
        "message": "Student deleted successfully"
    }