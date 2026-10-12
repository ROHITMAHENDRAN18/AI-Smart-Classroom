import asyncio
import time
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.routes.classroom_sessions import get_active_classroom_session
from backend.schemas.frame_inference import (
    FeatureAvailability,
    FrameInferenceResponse,
    InferenceFeatureStatuses,
)
from backend.services.frame_inference_service import (
    FrameInferenceBusyError,
    FrameInferenceService,
    InvalidFrameError,
    decode_jpeg,
)
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
                            int(
                                FRAME_MIN_INTERVAL_SECONDS
                                - (now - last_request_at)
                            ),
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
        detections = await asyncio.wait_for(
            run_in_threadpool(frame_inference_service.analyze, image),
            timeout=FRAME_INFERENCE_TIMEOUT_SECONDS,
        )
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
    return FrameInferenceResponse(
        session_id=session_id,
        classroom_id=classroom_id,
        frame_received_at=frame_received_at,
        processed_at=datetime.now(timezone.utc),
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
            face_detection=FeatureAvailability(
                status="not_connected",
                detail="Face detection is not connected to browser frame processing.",
            ),
            face_recognition=FeatureAvailability(
                status="not_connected",
                detail="Student identity recognition is not connected to this API.",
            ),
            tracking=FeatureAvailability(
                status="not_connected",
                detail="Tracking is not connected to browser frame processing.",
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
        detection_count=len(detections),
        results_persisted=False,
    )
