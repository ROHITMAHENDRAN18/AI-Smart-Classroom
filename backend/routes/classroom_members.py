from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom import Classroom
from backend.models.classroom_member import ClassroomMember
from backend.models.student import Student
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.schemas.classroom_member import (
    ClassroomMemberCreateRequest,
    ClassroomMemberResponse,
)


router = APIRouter(
    prefix="/classrooms",
    tags=["Classroom Members"],
)


def get_current_teacher(
    current_user: User,
    db: Session,
) -> Teacher:
    if current_user.role != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can manage classroom members",
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


@router.post(
    "/{classroom_id}/members",
    response_model=ClassroomMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_student_to_classroom(
    classroom_id: int,
    request: ClassroomMemberCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    student = (
        db.query(Student)
        .filter(
            Student.student_id == request.student_id,
        )
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    existing_member = (
        db.query(ClassroomMember)
        .filter(
            ClassroomMember.classroom_id == classroom_id,
            ClassroomMember.student_id == request.student_id,
        )
        .first()
    )

    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Student is already a member of this classroom",
            )

        existing_member.is_active = True

        db.commit()
        db.refresh(existing_member)

        return existing_member

    member = ClassroomMember(
        classroom_id=classroom_id,
        student_id=request.student_id,
        is_active=True,
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


@router.get(
    "/{classroom_id}/members",
    response_model=list[ClassroomMemberResponse],
)
def get_classroom_members(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
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
        .order_by(ClassroomMember.id)
        .all()
    )

    return members


@router.get(
    "/{classroom_id}/members/{student_id}",
    response_model=ClassroomMemberResponse,
)
def get_classroom_member(
    classroom_id: int,
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    member = (
        db.query(ClassroomMember)
        .filter(
            ClassroomMember.classroom_id == classroom_id,
            ClassroomMember.student_id == student_id,
            ClassroomMember.is_active.is_(True),
        )
        .first()
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student is not a member of this classroom",
        )

    return member


@router.delete(
    "/{classroom_id}/members/{student_id}",
    response_model=ClassroomMemberResponse,
)
def remove_student_from_classroom(
    classroom_id: int,
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teacher = get_current_teacher(
        current_user,
        db,
    )

    get_teacher_classroom(
        classroom_id,
        teacher.id,
        db,
    )

    member = (
        db.query(ClassroomMember)
        .filter(
            ClassroomMember.classroom_id == classroom_id,
            ClassroomMember.student_id == student_id,
            ClassroomMember.is_active.is_(True),
        )
        .first()
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student is not an active member of this classroom",
        )

    member.is_active = False

    db.commit()
    db.refresh(member)

    return member