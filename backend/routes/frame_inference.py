
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
from backend.models.classroom_member import ClassroomMember
from backend.models.classroom_session import ClassroomSession
from backend.models.attention_record import AttentionRecord
from backend.models.frame_inference_summary import FrameInferenceSummary
from backend.models.student import Student
from backend.models.user import User
from backend.routes.classroom_sessions import get_active_classroom_session
from backend.schemas.frame_inference import (
    FeatureAvailability,
    FrameInferenceResponse,
    FrameInferenceSummaryResponse,
    InferenceFeatureStatuses,
)
from backend.services.attendance_service import (
    record_automatic_attendance,
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
    DATABASE_ATTENTION_UPDATE_INTERVAL,
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


def persist_attention_observations(
    db: Session,
    session_id: str,
    faces: list[dict],
    recorded_at: datetime,
) -> tuple[bool, int]:
    """Persist verified-student observations at the configured cadence."""
    writes = 0
    try:
        seen_students: set[str] = set()
        for face in faces:
            student_id = face.get("student_id")
            if (
                face.get("recognition_status") != "recognized"
                or not student_id
                or student_id in seen_students
            ):
                continue
            seen_students.add(student_id)
            latest = (
                db.query(AttentionRecord)
                .filter(
                    AttentionRecord.session_id == session_id,
                    AttentionRecord.student_id == student_id,
                )
                .order_by(AttentionRecord.recorded_at.desc())
                .first()
            )
            if latest is not None and latest.recorded_at is not None:
                last_recorded = latest.recorded_at
                if last_recorded.tzinfo is None:
                    last_recorded = last_recorded.replace(tzinfo=timezone.utc)
                elapsed_seconds = (recorded_at - last_recorded).total_seconds()
                if elapsed_seconds < DATABASE_ATTENTION_UPDATE_INTERVAL:
                    continue
            state = face.get("attention_state", "UNKNOWN")
            score = face.get("attention_score")
            record = AttentionRecord(
                session_id=session_id,
                student_id=student_id,
                track_id=None,
                attention_state=state,
                attention_score=score,
                fusion_state=state,
                fusion_score=score,
                fusion_confidence=face.get("attention_confidence", 0.0),
                temporal_state=state,
                temporal_score=score,
                temporal_confidence=face.get("attention_confidence", 0.0),
                temporal_stable=False,
                confidence=face.get("attention_confidence", 0.0),
                recorded_at=recorded_at,
            )
            db.add(record)
            writes += 1
        if writes:
            db.commit()
        return True, writes
    except Exception:
        db.rollback()
        logger.exception(
            "attention_observation_persistence_failed session_id=%s",
            session_id,
        )
        return False, 0


def check_frame_rate_limit(user_id: int, session_id: str) -> None:
    global _last_rate_limit_cleanup

    now = time.monotonic()
    key = (user_id, session_id)

    with _rate_limit_lock:
        if now - _last_rate_limit_cleanup >= 60:
            expired_before = now - 60

            for previous_key, previous_time in list(
                _last_frame_at.items()
            ):
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


def verify_face_identities(
    db: Session,
    classroom_id: int,
    face_detections: list[dict],
) -> list[dict]:
    """
    Return an identity only if the recognition service explicitly
    recognizes a registered student who is actively enrolled
    in the requested classroom.

    Database eligibility checks do not guarantee model accuracy.
    """
    verified_faces: list[dict] = []

    for original_face in face_detections:
        face = dict(original_face)

        candidate_id = face.get("student_id")
        original_status = face.get("recognition_status")

        # Hide candidate identity until every check succeeds.
        face["student_id"] = None
        face["identity"] = "Unknown"
        face["similarity"] = None

        face["recognition_status"] = (
            "unavailable"
            if original_status == "unavailable"
            else "unknown"
        )

        if not candidate_id or original_status != "recognized":
            verified_faces.append(face)
            continue

        student = (
            db.query(Student)
            .filter(
                Student.student_id == candidate_id,
                Student.face_registered.is_(True),
            )
            .first()
        )

        if student is None:
            verified_faces.append(face)
            continue

        membership = (
            db.query(ClassroomMember)
            .filter(
                ClassroomMember.classroom_id == classroom_id,
                ClassroomMember.student_id == student.student_id,
                ClassroomMember.is_active.is_(True),
            )
            .first()
        )

        if membership is None:
            verified_faces.append(face)
            continue

        face["student_id"] = student.student_id
        face["identity"] = student.name or student.student_id
        face["recognition_status"] = "recognized"
        face["similarity"] = original_face.get("similarity")

        verified_faces.append(face)

    return verified_faces


def build_safe_face_summaries(
    face_detections: list[dict],
) -> list[dict]:
    """
    Persist only face-box metadata.

    Student IDs, names, similarity scores, and recognition statuses
    are never included in saved frame summaries.
    """
    allowed_keys = (
        "x1",
        "y1",
        "x2",
        "y2",
        "confidence",
        "quality",
    )

    return [
        {
            key: face[key]
            for key in allowed_keys
            if key in face
        }
        for face in face_detections
    ]


async def read_frame_payload(request: Request) -> bytes:
    content_type = request.headers.get("content-type", "")

    if (
        content_type.split(";", maxsplit=1)[0].strip().lower()
        != "image/jpeg"
    ):
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
            run_in_threadpool(
                frame_inference_service.analyze,
                image,
                session_id,
            ),
            timeout=FRAME_INFERENCE_TIMEOUT_SECONDS,
        )

        detections = inference_result["detections"]
        raw_face_detections = inference_result.get("faces", [])

        face_error = inference_result.get("face_error")
        recognition_error = inference_result.get("recognition_error")
        recognition_attempted = inference_result.get(
            "recognition_attempted",
            False,
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
            detail=(
                "Person detection timed out. Retry with a lower "
                "camera resolution."
            ),
        ) from error

    except Exception as error:
        logger.exception("Person detection failed for a classroom frame")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Person detection is unavailable. Check the configured "
                "model and retry."
            ),
        ) from error

    # Verify all identities against the student database and
    # active membership in this classroom.
    face_detections = verify_face_identities(
        db=db,
        classroom_id=classroom_id,
        face_detections=raw_face_detections,
    )

    unknown_detections = sum(
        1
        for face in face_detections
        if face.get("recognition_status") == "unknown"
    )

    # Automatic attendance is attempted only for verified identities.
    attendance_recorded = 0
    attendance_error = False

    try:
        for face in face_detections:
            student_id = face.get("student_id")

            if (
                face.get("recognition_status") != "recognized"
                or not student_id
            ):
                continue

            _, was_created = record_automatic_attendance(
                db=db,
                session_id=session_id,
                student_id=student_id,
                recorded_at=datetime.now(timezone.utc),
            )

            if was_created:
                attendance_recorded += 1

    except Exception:
        db.rollback()
        attendance_error = True

        logger.exception(
            "Automatic attendance recording failed for "
            "classroom_id=%s session_id=%s",
            classroom_id,
            session_id,
        )

    # Never persist identities or recognition scores in frame summaries.
    safe_face_detections = build_safe_face_summaries(
        face_detections
    )

    height, width = image.shape[:2]
    processed_at = datetime.now(timezone.utc)

    try:
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
            face_detections=safe_face_detections,
            face_detection_status=(
                "error" if face_error else "available"
            ),
            unknown_detections=unknown_detections,
        )
    except Exception:
        db.rollback()
        results_persisted = False

        logger.exception(
            "Frame summary persistence failed for "
            "classroom_id=%s session_id=%s",
            classroom_id,
            session_id,
        )

    attention_persisted, attention_recorded = persist_attention_observations(
        db, session_id, face_detections, processed_at
    )

    estimated_faces = [
        face
        for face in face_detections
        if face.get("attention_state") != "UNKNOWN"
    ]
    if estimated_faces:
        attention_inference = "available"
    elif not face_detections:
        attention_inference = "unknown"
    elif any(
        face.get("head_pose") or face.get("eye_state") != "UNKNOWN"
        for face in face_detections
    ):
        attention_inference = "partial"
    else:
        attention_inference = "unknown"

    primary_face = face_detections[0] if len(face_detections) == 1 else {}
    primary_pose = primary_face.get("head_pose") or {}
    attention_ready = inference_result.get("attention_fusion_available", False) and (
        inference_result.get("head_pose_available", False)
        or inference_result.get("eye_state_available", False)
    )
    attention_capability = FeatureAvailability(
        status="available" if attention_ready else "not_connected",
        detail=(
            "Available facial signals are fused per detected face; missing "
            "signals remain UNKNOWN."
            if attention_ready
            else "Attention models are unavailable in this backend environment."
        ),
    )

    face_detection_detail = (
        "The OpenCV Haar cascade processed the frame; it does not provide "
        "calibrated confidence scores."
        if not face_error
        else (
            "Face detection is unavailable in this frame. Install the "
            "project-pinned backend dependencies and restart the backend."
            if "OpenCV build does not include the Haar cascade API"
            in str(face_error)
            else (
                "Face detection failed for this frame. Check the backend "
                "log entry tagged face_detection_failed and retry."
            )
        )
    )

    if not recognition_attempted:
        recognition_status = "not_connected"
        recognition_detail = (
            "Face recognition was not attempted by the inference service."
        )
    elif recognition_error:
        recognition_status = "error"
        recognition_detail = (
            "Face recognition failed for this frame. Check the backend logs."
        )
    else:
        recognition_status = "available"
        recognition_detail = (
            "Face recognition ran. Only identities verified against the "
            "registered student database and active classroom membership "
            "are returned as recognized. Other faces remain Unknown."
        )

    if attendance_error:
        attendance_feature_status = "error"
        attendance_detail = (
            "An attendance database operation failed. Check backend logs."
        )
    elif not recognition_attempted or recognition_error:
        attendance_feature_status = "not_connected"
        attendance_detail = (
            "Automatic attendance requires working face recognition "
            "and verified student identities."
        )
    else:
        attendance_feature_status = "available"

        if attendance_recorded:
            attendance_detail = (
                f"{attendance_recorded} new automatic attendance record(s) "
                "were created for verified students. Existing records "
                "were preserved."
            )
        else:
            attendance_detail = (
                "Attendance integration is running. No new record was "
                "created for this frame. A verified student may not have "
                "been recognized, or attendance may already exist."
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
        attention_inference=attention_inference,
        attention_state=primary_face.get("attention_state", "UNKNOWN"),
        attention_score=primary_face.get("attention_score"),
        attention_confidence=primary_face.get("attention_confidence", 0.0),
        head_pose=primary_pose.get("head_pose", "UNKNOWN"),
        features=InferenceFeatureStatuses(
            person_detection=FeatureAvailability(
                status="available",
                detail=(
                    "The configured YOLO person detector processed this frame."
                ),
            ),
            result_persistence=FeatureAvailability(
                status="available" if results_persisted else "error",
                detail=(
                    "Bounding boxes and frame metadata were saved in a "
                    "bounded per-session summary; no image was stored."
                    if results_persisted
                    else (
                        "Detection succeeded, but the session summary could "
                        "not be saved. Check backend logs and database "
                        "migrations."
                    )
                ),
            ),
            face_detection=FeatureAvailability(
                status="error" if face_error else "available",
                detail=face_detection_detail,
            ),
            face_recognition=FeatureAvailability(
                status=recognition_status,
                detail=recognition_detail,
            ),
            tracking=FeatureAvailability(
                status="available",
                detail=(
                    "Session-scoped IoU association returned temporal "
                    "person track IDs. Track IDs are not student identities."
                ),
            ),
            attention_estimation=FeatureAvailability(
                status=attention_capability.status,
                detail=attention_capability.detail,
            ),
            head_pose_estimation=FeatureAvailability(
                status=(
                    "available"
                    if inference_result.get("head_pose_available")
                    else "not_connected"
                ),
                detail="Uses validated five-point facial keypoints when returned by face recognition.",
            ),
            eye_state_estimation=FeatureAvailability(
                status=(
                    "available"
                    if inference_result.get("eye_state_available")
                    else "not_connected"
                ),
                detail="Uses six-point eye contours from FaceMesh; no contours means UNKNOWN.",
            ),
            attention_persistence=FeatureAvailability(
                status="available" if attention_persisted else "error",
                detail=(
                    f"Persisted {attention_recorded} verified-student "
                    "observation(s) with a per-student cadence limit."
                    if attention_persisted
                    else "Attention observations could not be saved."
                ),
            ),
            attendance=FeatureAvailability(
                status=attendance_feature_status,
                detail=attendance_detail,
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
            .filter(
                FrameInferenceSummary.session_id == session_id
            )
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
            detail=(
                "The saved frame summary could not be loaded. Check "
                "backend logs and database migrations."
            ),
        ) from error

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No frame summary exists for this session",
        )

    available = FeatureAvailability(
        status="available",
        detail=(
            "The latest structured detections were loaded from "
            "the session summary."
        ),
    )

    unavailable_features = InferenceFeatureStatuses(
        person_detection=available,
        result_persistence=available,
        face_detection=FeatureAvailability(
            status=summary.face_detection_status,
            detail=(
                "The latest frame was processed by the OpenCV Haar detector; "
                "face confidence scores are uncalibrated or unavailable."
                if summary.face_detection_status == "available"
                else (
                    "The face detector could not process the latest frame "
                    "in the configured runtime."
                )
            ),
        ),
        face_recognition=FeatureAvailability(
            status="not_connected",
            detail=(
                "Identity results are not stored in the frame summary. "
                "Submit a new frame to obtain current recognition results."
            ),
        ),
        tracking=FeatureAvailability(
            status="available",
            detail=(
                "The latest person boxes include session-scoped temporal "
                "track IDs. Track IDs are not student identities."
            ),
        ),
        attention_estimation=FeatureAvailability(
            status="not_connected",
            detail="Attention estimation is not connected to this API.",
        ),
        head_pose_estimation=FeatureAvailability(
            status="not_connected",
            detail="Head-pose observations are not part of the saved frame summary.",
        ),
        eye_state_estimation=FeatureAvailability(
            status="not_connected",
            detail="Eye-state observations are not part of the saved frame summary.",
        ),
        attention_persistence=FeatureAvailability(
            status="available",
            detail="Attention persistence is available through the session history service.",
        ),
        attendance=FeatureAvailability(
            status="available",
            detail=(
                "Automatic attendance is handled during live frame "
                "processing. Student identities are intentionally not "
                "stored in frame summaries."
            ),
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
        attention_state="UNKNOWN",
        attention_score=None,
        attention_confidence=0.0,
        head_pose="UNKNOWN",
        features=unavailable_features,
        detections=summary.detections,
        face_detections=summary.face_detections or [],
        detection_count=summary.detection_count,
        results_persisted=True,
        frames_processed=summary.frames_processed,
        unknown_detections=summary.unknown_detections,
        updated_at=summary.updated_at,
    )
