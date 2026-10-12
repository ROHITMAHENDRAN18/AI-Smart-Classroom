from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.schemas.alerts import AlertResponse
from backend.services.alerts_service import get_attention_alerts
from backend.utils.logger import logger


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="List attention alerts",
    description=(
        "Returns persisted attention records whose state is NOT ATTENTIVE. "
        "Each matching record is returned as one alert; severity is null "
        "because the attention-record source does not store severity. "
        "Teachers only see records from their own classrooms; admins can "
        "see all classrooms. Supports limit (1-100), offset (>=0), and an "
        "optional session_id filter. Results are newest first."
    ),
)
def list_alerts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session_id: str | None = Query(default=None, min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    if current_user.role not in {"TEACHER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can view alerts",
        )

    try:
        teacher_id = None

        if current_user.role == "TEACHER":
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

            teacher_id = teacher.id

        return get_attention_alerts(
            db,
            limit=limit,
            offset=offset,
            session_id=session_id,
            teacher_id=teacher_id,
        )
    except SQLAlchemyError as error:
        logger.exception("Database failure while retrieving alerts")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert data is temporarily unavailable.",
        ) from error
