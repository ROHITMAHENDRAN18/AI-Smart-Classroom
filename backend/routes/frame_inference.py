import asyncio
import time
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.auth.classroom_access import require_classroom_access
from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.classroom_session import ClassroomSession
from backend.models.frame_inference_summary import FrameInferenceSummary
from backend.models.user import User
from backend.routes.classroom_sessions import get_active_classroom_session
from backend.schemas.frame_inference import (
    FeatureAvailability,
    FrameInferenceResponse,
    FrameInferenceSummaryResponse,
    InferenceFeatureStatuses,
)
from backend.services.frame_inference_service import (
    FrameInferenceBusyError,
    FrameInferenceService,
    InvalidFrameError,
    decode_jpeg,
)
from backend.services.frame_summary_service import persist_frame_summary
from backend.utils.logger import logger
from configs.settings import (
    FRAME_INFERENCE_TIMEOUT_SECONDS,
    FRAME_MAX_PAYLOAD_BYTES,
    FRAME_MIN_INTERVAL_SECONDS,
)

router = APIRouter(
    prefix="/classrooms",
    tags=["Frame Inference"],
)

_frame_size_limit_mb = FRAME_MAX_PAYLOAD_BYTES / (1024 * 1024)

_rate_limit_lock = Lock()
_last_frame_at: dict[tuple[int, str], float] = {}
_last_rate_limit_cleanup = 0.0
frame_inference_service = FrameInferenceService()


def check_frame_rate_limit(user_id: int, session_id: str) -> None:
    global _last_rate_limit_cleanup

    now = time.monotonic()
    key = (user_id, session_id)
    with _rate_limit_lock:
        if now - _last_rate_limit_cleanup >= 60:
            expired_before = now - 60
            for previous_key, previous_time in list(_last_frame_at.items()):
                if previous_time < expired_before:
                    _last_frame_at.pop(previous_key, None)
            _last_rate_limit_cleanup = now

        last_request_at = _last_frame_at.get(key)
        if (
            last_request_at is not None
            and now - last_request_at < FRAME_MIN_INTERVAL_SECONDS
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Frames are being submitted too frequently.",
                headers={
                    "Retry-After": str(
                        max(
                            1,
                            int(FRAME_MIN_INTERVAL_SECONDS - (now - last_request_at)),
                        )
                    )
                },
            )

        _last_frame_at[key] = now


async def read_frame_payload(request: Request) -> bytes:
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", maxsplit=1)[0].strip().lower() != "image/jpeg":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Frames must be uploaded as image/jpeg.",
        )

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The frame content length is invalid.",
            ) from error
        if declared_size < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The frame content length is invalid.",
            )
        if declared_size > FRAME_MAX_PAYLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    "The uploaded frame exceeds the configured "
                    f"{_frame_size_limit_mb:g} MB limit."
                ),
            )

    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > FRAME_MAX_PAYLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    "The uploaded frame exceeds the configured "
                    f"{_frame_size_limit_mb:g} MB limit."
                ),
            )
        payload.extend(chunk)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded frame is empty.",
        )

    return bytes(payload)


@router.post(
    "/{classroom_id}/sessions/{session_id}/frames",
    response_model=FrameInferenceResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "image/jpeg": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        }
    },
)
async def analyze_classroom_frame(
    classroom_id: int,
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active_session = get_active_classroom_session(
        classroom_id=classroom_id,
        current_user=current_user,
        db=db,
    )
    if active_session.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested session is not the active classroom session.",
        )

    check_frame_rate_limit(current_user.id, session_id)
    payload = await read_frame_payload(request)
    frame_received_at = datetime.now(timezone.utc)

    try:
        image = await run_in_threadpool(decode_jpeg, payload)
    except InvalidFrameError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    try:
        inference_started_at = time.perf_counter()
        inference_result = await asyncio.wait_for(
            run_in_threadpool(frame_inference_service.analyze, image, session_id),
            timeout=FRAME_INFERENCE_TIMEOUT_SECONDS,
        )
        detections = inference_result["detections"]
        face_detections = inference_result["faces"]
        inference_duration_ms = round(
            (time.perf_counter() - inference_started_at) * 1000,
            2,
        )
    except FrameInferenceBusyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Frame inference is busy. Retry shortly.",
            headers={"Retry-After": "2"},
        ) from error
    except TimeoutError as error:
        logger.warning("Person detection timed out for a classroom frame")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Person detection timed out. Retry with a lower camera resolution.",
        ) from error
    except Exception as error:
        logger.exception("Person detection failed for a classroom frame")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Person detection is unavailable. Check the configured model and retry.",
        ) from error

    height, width = image.shape[:2]
    processed_at = datetime.now(timezone.utc)
    results_persisted = persist_frame_summary(
        db,
        classroom_id=classroom_id,
        session_id=session_id,
        frame_received_at=frame_received_at,
        processed_at=processed_at,
        frame_width=width,
        frame_height=height,
        inference_duration_ms=inference_duration_ms,
        detections=detections,
        face_detections=face_detections,
        face_detection_status=(
            "error" if inference_result["face_error"] else "available"
        ),
    )
    return FrameInferenceResponse(
        session_id=session_id,
        classroom_id=classroom_id,
        frame_received_at=frame_received_at,
        processed_at=processed_at,
        frame_width=width,
        frame_height=height,
        processing_status="completed",
        inference_duration_ms=inference_duration_ms,
        pipeline="person_detection",
        attention_inference="not_connected",
        features=InferenceFeatureStatuses(
            person_detection=FeatureAvailability(
                status="available",
                detail="The configured YOLO person detector processed this frame.",
            ),
            result_persistence=FeatureAvailability(
                status="available" if results_persisted else "error",
                detail=(
                    "Latest bounding boxes and frame metadata were saved in a "
                    "bounded per-session summary; no image was stored."
                    if results_persisted
                    else (
                        "Detection succeeded, but the session summary could "
                        "not be saved. Check backend logs for the database "
                        "error and confirm the frame-summary migration has "
                        "been applied."
                    )
                ),
            ),
            face_detection=FeatureAvailability(
                status=("error" if inference_result["face_error"] else "available"),
                detail=(
                    "The OpenCV Haar cascade processed the frame; Haar does not provide calibrated confidence scores."
                    if not inference_result["face_error"]
                    else "Face detector failed to initialize or process this frame."
                ),
            ),
            face_recognition=FeatureAvailability(
                status="not_connected",
                detail="Student identity recognition is not connected to this API.",
            ),
            tracking=FeatureAvailability(
                status="available",
                detail="Session-scoped IoU association returned temporal person track IDs.",
            ),
            attention_estimation=FeatureAvailability(
                status="not_connected",
                detail="Attention estimation is not connected to this API.",
            ),
            attendance=FeatureAvailability(
                status="not_connected",
                detail="No identity-verified attendance operation is connected.",
            ),
        ),
        detections=detections,
        face_detections=face_detections,
        detection_count=len(detections),
        results_persisted=results_persisted,
    )


@router.get(
    "/{classroom_id}/sessions/{session_id}/frame-summary",
    response_model=FrameInferenceSummaryResponse,
)
def get_classroom_frame_summary(
    classroom_id: int,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_classroom_access(classroom_id, current_user, db)
    session = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.classroom_id == classroom_id,
            ClassroomSession.session_id == session_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom session not found",
        )

    try:
        summary = (
            db.query(FrameInferenceSummary)
            .filter(FrameInferenceSummary.session_id == session_id)
            .first()
        )
    except Exception as error:
        db.rollback()
        logger.exception(
            "frame_summary_read_failed classroom_id=%s session_id=%s",
            classroom_id,
            session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The saved frame summary could not be loaded. Check backend logs and database migrations.",
        ) from error

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No frame summary exists for this session",
        )

    available = FeatureAvailability(
        status="available",
        detail="The latest structured detections were loaded from the session summary.",
    )
    unavailable_features = InferenceFeatureStatuses(
        person_detection=available,
        result_persistence=available,
        face_detection=FeatureAvailability(
            status=summary.face_detection_status,
            detail=(
                "The latest frame was processed by the OpenCV Haar detector; scores are uncalibrated/unavailable."
                if summary.face_detection_status == "available"
                else "The face detector could not process the latest frame in the configured runtime."
            ),
        ),
        face_recognition=FeatureAvailability(
            status="not_connected",
            detail="Student identity recognition is not connected to this API.",
        ),
        tracking=FeatureAvailability(
            status="available",
            detail="The latest person boxes include session-scoped temporal track IDs.",
        ),
        attention_estimation=FeatureAvailability(
            status="not_connected",
            detail="Attention estimation is not connected to this API.",
        ),
        attendance=FeatureAvailability(
            status="not_connected",
            detail="No identity-verified attendance operation is connected.",
        ),
    )
    return FrameInferenceSummaryResponse(
        session_id=session_id,
        classroom_id=classroom_id,
        frame_received_at=summary.latest_frame_received_at,
        processed_at=summary.latest_processed_at,
        frame_width=summary.frame_width,
        frame_height=summary.frame_height,
        processing_status="completed",
        inference_duration_ms=summary.inference_duration_ms,
        pipeline="person_detection",
        attention_inference="not_connected",
        features=unavailable_features,
        detections=summary.detections,
        face_detections=summary.face_detections or [],
        detection_count=summary.detection_count,
        results_persisted=True,
        frames_processed=summary.frames_processed,
        updated_at=summary.updated_at,
    )
