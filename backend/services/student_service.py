from sqlalchemy.orm import Session

from backend.models.student import Student
from backend.schemas.student import StudentCreate
from backend.schemas.student import StudentUpdate


def create_student(db: Session, student: StudentCreate):
    """
    Create a new student.
    """

    db_student = Student(
        student_id=student.student_id,
        name=student.name,
        department=student.department,
        year=student.year,
        section=student.section,
        email=student.email,
    )

    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    return db_student


def get_students(db: Session):
    """
    Return all students.
    """

    return db.query(Student).all()


def get_student_by_id(
    db: Session,
    student_id: int,
):
    """
    Return one student.
    """

    return (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )


def update_student(
    db: Session,
    student_id: int,
    updated_student: StudentUpdate,
):
    """
    Update student.
    """

    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        return None

    update_data = updated_student.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)

    return student


def delete_student(
    db: Session,
    student_id: int,
):
    """
    Delete student.
    """

    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        return None

    db.delete(student)
    db.commit()

    return student