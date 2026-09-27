from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.attention_record import AttentionRecord


def record_attention(
    db: Session,
    session_id: str,
    student_id: str,
    track_id: int | None,
    attention_state: str,
    confidence: float | None = None,
    recorded_at: datetime | None = None,
):
    attention_record = AttentionRecord(
        session_id=session_id,
        student_id=student_id,
        track_id=track_id,
        attention_state=attention_state,
        confidence=confidence,
        recorded_at=recorded_at,
    )

    db.add(attention_record)
    db.commit()
    db.refresh(attention_record)

    return attention_record


def get_attention_for_session(
    db: Session,
    session_id: str,
):
    return (
        db.query(AttentionRecord)
        .filter(AttentionRecord.session_id == session_id)
        .order_by(AttentionRecord.recorded_at.asc())
        .all()
    )


def get_student_attention(
    db: Session,
    session_id: str,
    student_id: str,
):
    return (
        db.query(AttentionRecord)
        .filter(
            AttentionRecord.session_id == session_id,
            AttentionRecord.student_id == student_id,
        )
        .order_by(AttentionRecord.recorded_at.asc())
        .all()
    )


def delete_attention_for_session(
    db: Session,
    session_id: str,
):
    records = (
        db.query(AttentionRecord)
        .filter(AttentionRecord.session_id == session_id)
        .all()
    )

    for record in records:
        db.delete(record)

    db.commit()

    return len(records)