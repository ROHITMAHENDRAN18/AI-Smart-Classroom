from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.attention_record import AttentionRecord
from backend.models.classroom import Classroom
from backend.models.classroom_session import ClassroomSession
from backend.schemas.alerts import AlertResponse


def get_attention_alerts(
    db: Session,
    *,
    limit: int,
    offset: int,
    session_id: str | None = None,
    teacher_id: int | None = None,
) -> list[AlertResponse]:
    query = (
        db.query(AttentionRecord)
        .join(
            ClassroomSession,
            ClassroomSession.session_id == AttentionRecord.session_id,
        )
        .join(
            Classroom,
            Classroom.id == ClassroomSession.classroom_id,
        )
        .filter(
            func.upper(func.trim(AttentionRecord.attention_state))
            == "NOT ATTENTIVE"
        )
    )

    if session_id is not None:
        query = query.filter(
            AttentionRecord.session_id == session_id,
        )

    if teacher_id is not None:
        query = query.filter(
            Classroom.teacher_id == teacher_id,
        )

    records = (
        query.order_by(
            AttentionRecord.recorded_at.desc(),
            AttentionRecord.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        AlertResponse(
            alert_id=f"attention-{record.id}",
            alert_type=record.attention_state,
            message=(
                f"Student {record.student_id} was recorded as "
                f"{record.attention_state.lower()}."
            ),
            severity=None,
            timestamp=record.recorded_at,
            session_id=record.session_id,
            student_id=record.student_id,
            track_id=record.track_id,
        )
        for record in records
    ]
