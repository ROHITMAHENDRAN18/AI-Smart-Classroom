from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.classroom_session import ClassroomSession
from backend.models.frame_inference_summary import FrameInferenceSummary
from backend.utils.logger import logger


def persist_frame_summary(
    db: Session,
    *,
    classroom_id: int,
    session_id: str,
    frame_received_at: datetime,
    processed_at: datetime,
    frame_width: int,
    frame_height: int,
    inference_duration_ms: float,
    detections: list[dict],
    face_detections: list[dict] | None = None,
    face_detection_status: str = "error",
    unknown_detections: int = 0,
) -> bool:
    """Persist the latest boxes and a rolling frame count in one session row."""
    try:
        active_session = (
            db.query(ClassroomSession)
            .filter(
                ClassroomSession.classroom_id == classroom_id,
                ClassroomSession.session_id == session_id,
                ClassroomSession.status == "ACTIVE",
            )
            .with_for_update()
            .first()
        )
        if active_session is None:
            db.rollback()
            logger.warning(
                "frame_summary_persist_skipped classroom_id=%s session_id=%s "
                "reason=active_session_not_found",
                classroom_id,
                session_id,
            )
            return False

        summary = (
            db.query(FrameInferenceSummary)
            .filter(FrameInferenceSummary.session_id == session_id)
            .with_for_update()
            .first()
        )
        if summary is None:
            summary = FrameInferenceSummary(
                classroom_id=classroom_id,
                session_id=session_id,
                latest_frame_received_at=frame_received_at,
                latest_processed_at=processed_at,
                frame_width=frame_width,
                frame_height=frame_height,
                detection_count=len(detections),
                inference_duration_ms=inference_duration_ms,
                detections=detections,
                face_detections=face_detections or [],
                face_detection_status=face_detection_status,
                unknown_detections=unknown_detections,
                frames_processed=1,
            )
            db.add(summary)
        else:
            summary.latest_frame_received_at = frame_received_at
            summary.latest_processed_at = processed_at
            summary.frame_width = frame_width
            summary.frame_height = frame_height
            summary.detection_count = len(detections)
            summary.inference_duration_ms = inference_duration_ms
            summary.detections = detections
            summary.face_detections = face_detections or []
            summary.face_detection_status = face_detection_status
            summary.unknown_detections += unknown_detections
            summary.frames_processed += 1

        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "frame_summary_persist_failed classroom_id=%s session_id=%s",
            classroom_id,
            session_id,
        )
        return False
