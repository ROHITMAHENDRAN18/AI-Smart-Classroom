from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
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
    db: Session = Depends(get_db)
):

    return get_all_students_analytics(db)


# ============================================================
# CLASSROOM ANALYTICS
# ============================================================

@router.get("/classroom")
def classroom_analytics(
    db: Session = Depends(get_db)
):

    return get_classroom_analytics(db)


# ============================================================
# STUDENT ATTENTION TIMELINE
# ============================================================

@router.get(
    "/students/{student_id}/timeline"
)
def student_attention_timeline(
    student_id: str,
    db: Session = Depends(get_db)
):

    student = get_student_analytics(
        db,
        student_id
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
            student_id
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
    db: Session = Depends(get_db)
):

    result = get_student_analytics(
        db,
        student_id
    )

    if result["student_name"] is None:

        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return result