from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom import Classroom
from backend.models.classroom_member import ClassroomMember
from backend.models.classroom_session import ClassroomSession
from backend.models.student import Student
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.schemas.classroom_overview import (
    ClassroomOverviewResponse,
    ClassroomOverviewSession,
    ClassroomOverviewStudent,
)


router = APIRouter(
    prefix="/classrooms",
    tags=["Classroom Overview"],
)


def get_current_teacher(
    current_user: User,
    db: Session,
) -> Teacher:
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access classroom overview",
        )

    teacher = (
        db.query(Teacher)
        .filter(
            Teacher.user_id == current_user.id,
        )
        .first()
    )

    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found",
        )

    return teacher


def get_teacher_classroom(
    classroom_id: int,
    teacher_id: int,
    db: Session,
) -> Classroom:
    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == classroom_id,
            Classroom.teacher_id == teacher_id,
        )
        .first()
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )

    if not classroom.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Classroom is inactive",
        )

    return classroom


@router.get(
    "/{classroom_id}/overview",
    response_model=ClassroomOverviewResponse,
)
def get_classroom_overview(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    classroom = get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    members = (
    db.query(ClassroomMember)
    .filter(
        ClassroomMember.classroom_id == classroom_id,
        ClassroomMember.is_active.is_(True),
    )
    .order_by(
        ClassroomMember.id.asc(),
    )
    .all()
)
    students = []

    for member in members:
        student = (
            db.query(Student)
            .filter(
                Student.student_id == member.student_id,
            )
            .first()
        )

        if student is None:
            continue

        students.append(
            ClassroomOverviewStudent(
                student_id=student.student_id,
                name=student.name,
                department=student.department,
                year=student.year,
                section=student.section,
                email=student.email,
                face_registered=student.face_registered,
                is_active=member.is_active,
            )
        )

    active_session = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.classroom_id == classroom_id,
            ClassroomSession.status == "ACTIVE",
        )
        .order_by(
            ClassroomSession.id.desc(),
        )
        .first()
    )

    active_session_response = None

    if active_session is not None:
        active_session_response = ClassroomOverviewSession(
            id=active_session.id,
            session_id=active_session.session_id,
            classroom_id=active_session.classroom_id,
            started_at=active_session.started_at,
            ended_at=active_session.ended_at,
            duration_seconds=active_session.duration_seconds,
            status=active_session.status,
            created_at=active_session.created_at,
        )

    return ClassroomOverviewResponse(
        classroom_id=classroom.id,
        classroom_code=classroom.classroom_code,
        classroom_name=classroom.name,
        department=classroom.department,
        year=classroom.year,
        section=classroom.section,
        teacher_id=classroom.teacher_id,
        is_active=classroom.is_active,
        total_students=len(students),
        active_students=len(students),
        students=students,
        active_session=active_session_response,
    )