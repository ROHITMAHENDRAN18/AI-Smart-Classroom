from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.schemas.student import StudentCreate
from backend.schemas.student import StudentResponse
from fastapi import HTTPException
from backend.services.student_service import (
    create_student,
    get_students,
    get_student_by_id,
)

router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=201,
)
def add_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new student.
    """
    return create_student(db, student)
@router.get(
    "/",
    response_model=list[StudentResponse],
)
def list_students(
    db: Session = Depends(get_db),
):
    """
    Get all students.
    """
    return get_students(db)
@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Get one student by ID.
    """

    student = get_student_by_id(db, student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return student