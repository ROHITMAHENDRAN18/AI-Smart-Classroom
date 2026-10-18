
import cv2
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from configs.settings import (
    FRAME_MAX_PAYLOAD_BYTES,
    FRAME_MAX_WIDTH,
    FRAME_MAX_HEIGHT,
    FRAME_MAX_PIXELS,
)
from backend.auth.classroom_access import (
    get_owned_classroom_ids,
    require_classroom_access,
)
from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom import Classroom
from backend.models.classroom_member import ClassroomMember
from backend.models.student import Student
from backend.models.user import User
from backend.schemas.student import (
    StudentCreateRequest,
    StudentResponse,
    StudentUpdateRequest,
)
from backend.services.face_recognition_service import face_recognition_service


router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


def require_teacher_or_admin(
    current_user: User,
) -> None:
    if current_user.role not in {"TEACHER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can manage students",
        )


def require_student_classroom_access(
    student_id: str,
    current_user: User,
    db: Session,
) -> None:
    if current_user.role == "ADMIN":
        return

    classroom_ids = get_owned_classroom_ids(current_user, db)

    membership = (
        db.query(ClassroomMember.id)
        .filter(
            ClassroomMember.student_id == student_id,
            ClassroomMember.classroom_id.in_(classroom_ids or []),
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
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
    classroom_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_teacher_or_admin(current_user)

    if classroom_id is not None:
        require_classroom_access(classroom_id, current_user, db)

        members = (
            db.query(Student, ClassroomMember.is_active)
            .join(
                ClassroomMember,
                ClassroomMember.student_id == Student.student_id,
            )
            .filter(
                ClassroomMember.classroom_id == classroom_id,
            )
            .order_by(Student.id)
            .all()
        )

        return [
            {
                **{
                    field: getattr(student, field)
                    for field in (
                        "id",
                        "student_id",
                        "name",
                        "department",
                        "year",
                        "section",
                        "email",
                        "face_registered",
                    )
                },
                "classroom_is_active": membership_is_active,
            }
            for student, membership_is_active in members
        ]

    owned_classroom_ids = get_owned_classroom_ids(current_user, db)

    if owned_classroom_ids is None:
        return (
            db.query(Student)
            .order_by(Student.id)
            .all()
        )

    return (
        db.query(Student)
        .join(
            ClassroomMember,
            ClassroomMember.student_id == Student.student_id,
        )
        .join(
            Classroom,
            Classroom.id == ClassroomMember.classroom_id,
        )
        .filter(
            Classroom.id.in_(owned_classroom_ids),
            ClassroomMember.is_active.is_(True),
        )
        .distinct()
        .order_by(Student.id)
        .all()
    )


@router.post(
    "/{student_id}/face",
    status_code=status.HTTP_200_OK,
)
async def enroll_student_face(
    student_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enroll a student's face using a JPEG image captured from a webcam.

    The endpoint stores the face embedding, not the original image.
    """

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

    require_student_classroom_access(
        student_id,
        current_user,
        db,
    )

    content_type = request.headers.get("content-type", "")

    if content_type.split(";")[0].strip().lower() != "image/jpeg":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG image captured from the webcam.",
        )

    payload = await request.body()

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is empty.",
        )

    if len(payload) > FRAME_MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The uploaded image exceeds the allowed size.",
        )

    if not payload.startswith(b"\xff\xd8"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is not a valid JPEG.",
        )

    image = cv2.imdecode(
        np.frombuffer(payload, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None or image.ndim != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The JPEG image could not be decoded.",
        )

    height, width = image.shape[:2]

    if (
        width < 1
        or height < 1
        or width > FRAME_MAX_WIDTH
        or height > FRAME_MAX_HEIGHT
        or width * height > FRAME_MAX_PIXELS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The image dimensions exceed the supported limits.",
        )

    try:
        result = face_recognition_service.enroll(
            student.student_id,
            image,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face enrollment is temporarily unavailable.",
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The face embedding could not be saved.",
        ) from error

    try:
        student.face_registered = True
        db.commit()
        db.refresh(student)
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The face embedding was generated, but the student record "
                "could not be updated. Please retry enrollment."
            ),
        ) from error

    return {
        "message": "Face enrollment completed successfully.",
        "student_id": student.student_id,
        "face_registered": student.face_registered,
        "embedding_dimensions": result["embedding_dimensions"],
    }


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

    require_student_classroom_access(student_id, current_user, db)

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

    require_student_classroom_access(student_id, current_user, db)

    update_data = request.model_dump(exclude_unset=True)

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

    require_student_classroom_access(student_id, current_user, db)

    student.face_registered = False

    db.commit()
    db.refresh(student)

    return student
