from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth.classroom_access import (
    get_owned_classroom_ids,
    require_classroom_access,
)
from backend.auth.dependencies import get_current_user
from backend.models.classroom_member import ClassroomMember
from backend.models.student import Student
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.analytics import StudentAnalyticsResponse
from backend.services.analytics_service import (
    get_all_students_analytics,
    get_student_analytics,
    get_student_attention_timeline,
    get_classroom_analytics,
)


# ============================================================
# ANALYTICS ROUTER
# ============================================================

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


# ============================================================
# ALL STUDENTS ANALYTICS
# ============================================================

@router.get(
    "/students",
    response_model=list[StudentAnalyticsResponse]
)
def list_student_analytics(
    classroom_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if classroom_id is not None:
        require_classroom_access(classroom_id, current_user, db)
        classroom_ids = [classroom_id]
    else:
        classroom_ids = get_owned_classroom_ids(current_user, db)
    return get_all_students_analytics(db, classroom_ids)


# ============================================================
# CLASSROOM ANALYTICS
# ============================================================

@router.get("/classroom")
def classroom_analytics(
    classroom_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if classroom_id is not None:
        require_classroom_access(classroom_id, current_user, db)
        classroom_ids = [classroom_id]
    else:
        classroom_ids = get_owned_classroom_ids(current_user, db)
    return get_classroom_analytics(db, classroom_ids)


# ============================================================
# STUDENT ATTENTION TIMELINE
# ============================================================

@router.get(
    "/students/{student_id}/timeline"
)
def student_attention_timeline(
    student_id: str,
    classroom_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    classroom_ids = _get_student_classroom_scope(
        student_id,
        classroom_id,
        current_user,
        db,
    )
    student = get_student_analytics(
        db,
        student_id,
        classroom_ids,
    )

    if student["student_name"] is None:

        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return {
        "student_id": student_id,
        "timeline": get_student_attention_timeline(
            db,
            student_id,
            classroom_ids,
        )
    }


# ============================================================
# SINGLE STUDENT ANALYTICS
# ============================================================

@router.get(
    "/students/{student_id}",
    response_model=StudentAnalyticsResponse
)
def student_analytics(
    student_id: str,
    classroom_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    classroom_ids = _get_student_classroom_scope(
        student_id,
        classroom_id,
        current_user,
        db,
    )
    result = get_student_analytics(
        db,
        student_id,
        classroom_ids,
    )

    if result["student_name"] is None:

        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return result


def _get_student_classroom_scope(
    student_id: str,
    classroom_id: int | None,
    current_user: User,
    db: Session,
) -> list[int] | None:
    if classroom_id is not None:
        require_classroom_access(classroom_id, current_user, db)
        classroom_ids = [classroom_id]
    else:
        classroom_ids = get_owned_classroom_ids(current_user, db)

    query = db.query(Student.student_id).filter(
        Student.student_id == student_id
    )
    if classroom_ids is not None:
        query = (
            query.join(
                ClassroomMember,
                ClassroomMember.student_id == Student.student_id,
            )
            .filter(ClassroomMember.classroom_id.in_(classroom_ids))
        )
    if query.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return classroom_ids