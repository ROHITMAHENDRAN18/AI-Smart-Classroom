import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from backend.app.main import app
from backend.auth.dependencies import get_current_user
from backend.database.base import Base
from backend.database.session import get_db
from backend.models.attendance_record import AttendanceRecord
from backend.models.attention_record import AttentionRecord
from backend.models.classroom import Classroom
from backend.models.classroom_session import ClassroomSession
from backend.models.frame_inference_summary import FrameInferenceSummary
from backend.models.teacher import Teacher
from backend.models.user import User
from backend.routes import frame_inference as frame_route
from backend.services.frame_inference_service import (
    FrameInferenceBusyError,
    FrameInferenceService,
    IoUTrackManager,
    InvalidFrameError,
    decode_jpeg,
)
from backend.services.frame_summary_service import persist_frame_summary
from configs.settings import API_VERSION


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def tolist(self):
        return self.value


class FakeDetector:
    def detect(self, _image):
        return [
            SimpleNamespace(
                boxes=SimpleNamespace(
                    xyxy=FakeTensor(
                        [
                            [-5, 10, 45, 90],
                            [70, 20, 60, 50],
                            [1, 1, 10, 10],
                        ]
                    ),
                    conf=FakeTensor([0.9, 0.8, float("nan")]),
                )
            )
        ]


class StubInferenceService:
    def analyze(self, _image, _session_id="default"):
        return {
            "detections": [
                {
                    "class_label": "person",
                    "x1": 1.0,
                    "y1": 2.0,
                    "x2": 30.0,
                    "y2": 40.0,
                    "confidence": 0.91,
                    "track_id": 1,
                }
            ],
            "faces": [],
            "face_error": None,
        }


@pytest.fixture
def frame_context(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    user = User(
        id=1,
        username="frame-teacher",
        email="frame-teacher@example.test",
        password_hash="not-used",
        role="TEACHER",
        is_active=True,
    )
    db.add(user)
    db.flush()
    teacher = Teacher(
        user_id=user.id,
        teacher_id="FRAME_T1",
        name="Frame Teacher",
        department="Computing",
    )
    db.add(teacher)
    db.flush()
    classroom = Classroom(
        classroom_code="FRAME_C1",
        name="Frame Classroom",
        department="Computing",
        year=1,
        section="A",
        teacher_id=teacher.id,
        is_active=True,
    )
    db.add(classroom)
    db.flush()
    active_session = ClassroomSession(
        session_id="SESSION_FRAME_ACTIVE",
        classroom_id=classroom.id,
        started_at=datetime.now(timezone.utc),
        status="ACTIVE",
    )
    db.add(active_session)
    db.commit()

    monkeypatch.setattr(
        "backend.routes.frame_inference.frame_inference_service",
        StubInferenceService(),
    )
    with frame_route._rate_limit_lock:
        frame_route._last_frame_at.clear()
        frame_route._last_rate_limit_cleanup = 0.0

    try:
        yield db, user, classroom, active_session
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def jpeg_frame(width=64, height=48):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    successful, encoded = cv2.imencode(".jpg", image)
    assert successful
    return encoded.tobytes()


def make_request(payload, content_type):
    consumed = False

    async def receive():
        nonlocal consumed
        if consumed:
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }
        consumed = True
        return {
            "type": "http.request",
            "body": payload,
            "more_body": False,
        }

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/frames",
            "raw_path": b"/frames",
            "query_string": b"",
            "headers": [
                (b"content-type", content_type.encode("ascii")),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
            "client": ("test", 1234),
            "server": ("test", 80),
        },
        receive,
    )


async def make_asgi_request(path, payload, headers):
    request_messages = [
        {
            "type": "http.request",
            "body": payload,
            "more_body": False,
        }
    ]
    response_messages = []

    async def receive():
        if request_messages:
            return request_messages.pop(0)
        return {"type": "http.disconnect"}

    async def send(message):
        response_messages.append(message)

    raw_path = path.encode("ascii")
    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": raw_path,
            "query_string": b"",
            "headers": headers,
            "client": ("test", 1234),
            "server": ("test", 80),
        },
        receive,
        send,
    )
    status_code = next(
        message["status"]
        for message in response_messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in response_messages
        if message["type"] == "http.response.body"
    )
    return status_code, response_body


def post_frame(
    db,
    user,
    classroom,
    session,
    payload=None,
    content_type="image/jpeg",
):
    frame_payload = jpeg_frame() if payload is None else payload
    return asyncio.run(
        frame_route.analyze_classroom_frame(
            classroom_id=classroom.id,
            session_id=session.session_id,
            request=make_request(frame_payload, content_type),
            current_user=user,
            db=db,
        )
    )


def test_frame_service_returns_only_valid_person_boxes():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    detections = FrameInferenceService(
        detector_factory=FakeDetector,
    ).analyze(image)

    assert detections["detections"] == [
        {
            "class_label": "person",
            "x1": 0.0,
            "y1": 10.0,
            "x2": 45.0,
            "y2": 90.0,
            "confidence": 0.9,
            "track_id": 1,
        }
    ]
    assert detections["faces"] == []


def test_attention_requires_real_signals_and_returns_unknown_when_missing(monkeypatch):
    from backend.services import frame_inference_service as module

    monkeypatch.setattr(module, "detect_eye_state_from_face", lambda _crop: {"eye_state": "UNKNOWN"})
    result = module._estimate_attention(
        np.zeros((40, 40, 3), dtype=np.uint8),
        {"x1": 0, "y1": 0, "x2": 40, "y2": 40},
        None,
    )
    assert result["attention_state"] == "UNKNOWN"
    assert result["attention_score"] is None
    assert result["attention_confidence"] == 0


def test_attention_fuses_only_an_available_eye_signal(monkeypatch):
    from backend.services import frame_inference_service as module

    monkeypatch.setattr(module, "detect_eye_state_from_face", lambda _crop: {"eye_state": "OPEN"})
    result = module._estimate_attention(
        np.zeros((40, 40, 3), dtype=np.uint8),
        {"x1": 0, "y1": 0, "x2": 40, "y2": 40},
        None,
    )
    assert result["eye_state"] == "OPEN"
    assert result["attention_state"] == "ATTENTIVE"
    assert result["attention_score"] == 1
    assert result["attention_confidence"] == pytest.approx(0.3)


def test_frame_service_rejects_concurrent_model_use():
    service = FrameInferenceService(detector_factory=FakeDetector)
    service._inference_lock.acquire()
    try:
        with pytest.raises(FrameInferenceBusyError):
            service.analyze(np.zeros((10, 10, 3), dtype=np.uint8))
    finally:
        service._inference_lock.release()


def test_iou_tracker_keeps_ids_through_a_missed_frame_and_expires():
    tracker = IoUTrackManager(max_missed=1, min_iou=0.1)
    first = {"x1": 0, "y1": 0, "x2": 20, "y2": 20}
    track_id = tracker.update([first])[0]["track_id"]
    moved = {"x1": 1, "y1": 0, "x2": 21, "y2": 20}
    assert tracker.update([moved])[0]["track_id"] == track_id
    assert tracker.update([]) == []
    returned = {"x1": 2, "y1": 0, "x2": 22, "y2": 20}
    assert tracker.update([returned])[0]["track_id"] == track_id
    tracker.update([])
    tracker.update([])
    fresh = {"x1": 2, "y1": 0, "x2": 22, "y2": 20}
    assert tracker.update([fresh])[0]["track_id"] != track_id


def test_face_detector_processes_no_face_frame_and_maps_multiple_boxes(monkeypatch):
    service = FrameInferenceService(detector_factory=FakeDetector)

    class FakeCascade:
        def detectMultiScale(self, _gray, **_kwargs):
            return [(2, 3, 10, 11), (30, 20, 40, 30)]

    service._face_cascade = FakeCascade()
    faces = service._detect_faces(np.zeros((64, 80, 3), dtype=np.uint8))
    assert len(faces) == 2

    assert faces[1] == {
    "x1": 30,
    "y1": 20,
    "x2": 70,
    "y2": 50,
    "confidence": None,
    "quality": "detected_unscored",
    "landmarks": None,
}

    class EmptyCascade:
        def detectMultiScale(self, _gray, **_kwargs):
            return ()

    service._face_cascade = EmptyCascade()
    no_faces = service._detect_faces(np.zeros((64, 80, 3), dtype=np.uint8))
    assert no_faces == []


def test_face_detector_reports_opencv_build_without_cascade_api(monkeypatch):
    monkeypatch.delattr(cv2, "CascadeClassifier", raising=False)
    service = FrameInferenceService(detector_factory=FakeDetector)

    with pytest.raises(RuntimeError, match="does not include the Haar cascade API"):
        service._get_face_cascade()


def test_face_detector_uses_installed_cascade_when_project_xml_is_empty(
    monkeypatch, tmp_path
):
    if not hasattr(cv2, "CascadeClassifier"):
        pytest.skip("Installed OpenCV build has no Haar cascade API")
    empty_cascade = tmp_path / "empty.xml"
    empty_cascade.write_bytes(b"")
    monkeypatch.setattr(
        "backend.services.frame_inference_service.FACE_CASCADE_PATH",
        empty_cascade,
    )
    service = FrameInferenceService(detector_factory=FakeDetector)

    cascade = service._get_face_cascade()
    assert not cascade.empty()
    assert service._detect_faces(np.zeros((96, 96, 3), dtype=np.uint8)) == []


def test_jpeg_decoder_rejects_invalid_and_oversized_images():
    with pytest.raises(InvalidFrameError):
        decode_jpeg(b"not an image")

    oversized = np.zeros((1441, 1441, 3), dtype=np.uint8)
    successful, encoded = cv2.imencode(".jpg", oversized)
    assert successful
    with pytest.raises(InvalidFrameError):
        decode_jpeg(encoded.tobytes())


def test_frame_endpoint_persists_bounded_summary_without_storing_images(
    frame_context,
):
    db, user, classroom, session = frame_context

    result = post_frame(db, user, classroom, session)

    assert result.session_id == session.session_id
    assert result.classroom_id == classroom.id
    assert result.processing_status == "completed"
    assert result.frame_received_at is not None
    assert result.processed_at is not None
    assert result.inference_duration_ms >= 0
    assert result.pipeline == "person_detection"
    assert result.attention_inference == "unknown"
    assert result.attention_state == "UNKNOWN"
    assert result.attention_score is None
    assert result.attention_confidence == 0
    assert result.features.person_detection.status == "available"
    assert result.features.face_recognition.status == "not_connected"
    assert result.features.attention_estimation.status == "not_connected"
    assert result.features.attention_persistence.status == "available"
    assert result.features.attendance.status == "not_connected"
    assert result.detection_count == len(result.detections) == 1
    assert result.detections[0].class_label == "person"
    assert result.detections[0].confidence == 0.91
    assert result.frame_width == 64
    assert result.frame_height == 48
    assert result.results_persisted is True
    assert result.features.result_persistence.status == "available"
    assert db.query(AttendanceRecord).count() == 0
    assert db.query(AttentionRecord).count() == 0
    assert db.query(ClassroomSession).count() == 1
    summary = db.query(FrameInferenceSummary).one()
    assert summary.session_id == session.session_id
    assert summary.frames_processed == 1
    assert summary.unknown_detections == 0
    assert summary.detection_count == 1
    assert summary.detections[0]["class_label"] == "person"
    retrieved = frame_route.get_classroom_frame_summary(
        classroom.id,
        session.session_id,
        user,
        db,
    )
    assert retrieved.results_persisted is True
    assert retrieved.frames_processed == 1
    assert retrieved.unknown_detections == 0
    assert retrieved.detection_count == 1


def test_frame_endpoint_counts_only_unknown_face_observations(
    frame_context,
    monkeypatch,
):
    db, user, classroom, session = frame_context
    faces = [
        {
            "x1": 1,
            "y1": 1,
            "x2": 10,
            "y2": 10,
            "quality": "detected_unscored",
            "recognition_status": recognition_status,
        }
        for recognition_status in (
            "unknown",
            "unknown",
            "recognized",
            "unavailable",
        )
    ]

    class FacesInferenceService(StubInferenceService):
        def analyze(self, _image, _session_id="default"):
            result = super().analyze(_image, _session_id)
            result["faces"] = faces
            return result

    monkeypatch.setattr(
        frame_route,
        "frame_inference_service",
        FacesInferenceService(),
    )
    monkeypatch.setattr(
        frame_route,
        "verify_face_identities",
        lambda **kwargs: kwargs["face_detections"],
    )

    result = post_frame(db, user, classroom, session)

    assert result.results_persisted is True
    summary = db.query(FrameInferenceSummary).one()
    assert summary.unknown_detections == 2
    response = frame_route.get_classroom_frame_summary(
        classroom.id,
        session.session_id,
        user,
        db,
    )
    assert response.unknown_detections == 2


def test_frame_summary_persistence_failure_is_reported_without_failing_inference(
    frame_context,
    monkeypatch,
):
    db, user, classroom, session = frame_context
    monkeypatch.setattr(
        frame_route,
        "persist_frame_summary",
        lambda *_args, **_kwargs: False,
    )

    result = post_frame(db, user, classroom, session)

    assert result.processing_status == "completed"
    assert result.detection_count == 1
    assert result.results_persisted is False
    assert result.features.result_persistence.status == "error"
    assert db.query(FrameInferenceSummary).count() == 0


def test_attention_persistence_is_verified_student_scoped_and_rate_limited(
    frame_context, monkeypatch
):
    db, _user, _classroom, session = frame_context
    from backend.routes.frame_inference import persist_attention_observations

    monkeypatch.setattr(frame_route, "DATABASE_ATTENTION_UPDATE_INTERVAL", 10)
    face = {
        "student_id": "S_ATTENTION",
        "recognition_status": "recognized",
        "attention_state": "ATTENTIVE",
        "attention_score": 0.9,
        "attention_confidence": 0.3,
    }
    start = datetime.now(timezone.utc)
    assert persist_attention_observations(db, session.session_id, [face], start) == (True, 1)
    assert persist_attention_observations(
        db, session.session_id, [face], start + timedelta(seconds=2)
    ) == (True, 0)
    assert persist_attention_observations(
        db, session.session_id, [face], start + timedelta(seconds=11)
    ) == (True, 1)
    records = db.query(AttentionRecord).all()
    assert len(records) == 2
    assert all(record.student_id == "S_ATTENTION" for record in records)
    assert all(record.attention_score == 0.9 for record in records)


def test_frame_summary_updates_one_row_per_session(frame_context):
    db, user, classroom, session = frame_context
    first_time = datetime.now(timezone.utc)
    second_time = datetime.now(timezone.utc)
    first_detection = {
        "class_label": "person",
        "x1": 1.0,
        "y1": 2.0,
        "x2": 30.0,
        "y2": 40.0,
        "confidence": 0.91,
    }

    assert persist_frame_summary(
        db,
        classroom_id=classroom.id,
        session_id=session.session_id,
        frame_received_at=first_time,
        processed_at=first_time,
        frame_width=64,
        frame_height=48,
        inference_duration_ms=12.5,
        detections=[first_detection],
        unknown_detections=2,
    )
    assert persist_frame_summary(
        db,
        classroom_id=classroom.id,
        session_id=session.session_id,
        frame_received_at=second_time,
        processed_at=second_time,
        frame_width=64,
        frame_height=48,
        inference_duration_ms=9.5,
        detections=[],
        unknown_detections=1,
    )

    summaries = db.query(FrameInferenceSummary).all()
    assert len(summaries) == 1
    assert summaries[0].frames_processed == 2
    assert summaries[0].unknown_detections == 3
    assert summaries[0].detection_count == 0
    assert summaries[0].inference_duration_ms == 9.5
    assert summaries[0].detections == []
    stored_timestamp = summaries[0].latest_frame_received_at
    if stored_timestamp.tzinfo is None:
        stored_timestamp = stored_timestamp.replace(tzinfo=timezone.utc)
    assert stored_timestamp == second_time
    response = frame_route.get_classroom_frame_summary(
        classroom.id,
        session.session_id,
        user,
        db,
    )
    assert response.unknown_detections == 3


def test_http_frame_endpoint_requires_authentication_and_serializes_results(
    frame_context,
):
    db, user, classroom, session = frame_context
    payload = jpeg_frame()
    path = (
        f"{API_VERSION.rstrip('/')}/classrooms/{classroom.id}/sessions/"
        f"{session.session_id}/frames"
    )
    headers = [
        (b"content-type", b"image/jpeg"),
        (b"content-length", str(len(payload)).encode("ascii")),
    ]

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        status_code, _ = asyncio.run(make_asgi_request(path, payload, headers))
        assert status_code == 401

        app.dependency_overrides[get_current_user] = lambda: user
        status_code, body = asyncio.run(make_asgi_request(path, payload, headers))
    finally:
        app.dependency_overrides.clear()

    assert status_code == 200
    result = json.loads(body)
    assert result["session_id"] == session.session_id
    assert result["processing_status"] == "completed"
    assert result["features"]["person_detection"]["status"] == "available"
    assert result["features"]["face_recognition"]["status"] == "not_connected"
    assert result["detections"][0]["class_label"] == "person"


def test_frame_endpoint_requires_teacher_owned_active_session(frame_context):
    db, user, classroom, session = frame_context

    user.role = "STUDENT"
    db.commit()
    with pytest.raises(HTTPException) as forbidden:
        post_frame(db, user, classroom, session)
    assert forbidden.value.status_code == 403

    user.role = "TEACHER"
    session.status = "COMPLETED"
    db.commit()
    with pytest.raises(HTTPException) as missing:
        post_frame(db, user, classroom, session)
    assert missing.value.status_code == 404


def test_frame_endpoint_rejects_another_teachers_classroom(frame_context):
    db, user, classroom, _ = frame_context
    other_user = User(
        id=2,
        username="other-frame-teacher",
        email="other-frame-teacher@example.test",
        password_hash="not-used",
        role="TEACHER",
        is_active=True,
    )
    db.add(other_user)
    db.flush()
    other_teacher = Teacher(
        user_id=other_user.id,
        teacher_id="FRAME_T2",
        name="Other Frame Teacher",
        department="Computing",
    )
    db.add(other_teacher)
    db.flush()
    other_classroom = Classroom(
        classroom_code="FRAME_C2",
        name="Other Frame Classroom",
        department="Computing",
        year=1,
        section="B",
        teacher_id=other_teacher.id,
        is_active=True,
    )
    db.add(other_classroom)
    db.flush()
    other_session = ClassroomSession(
        session_id="SESSION_FRAME_OTHER",
        classroom_id=other_classroom.id,
        started_at=datetime.now(timezone.utc),
        status="ACTIVE",
    )
    db.add(other_session)
    db.commit()

    with pytest.raises(HTTPException) as forbidden:
        post_frame(db, user, other_classroom, other_session)

    assert classroom.id != other_classroom.id
    assert forbidden.value.status_code == 404


@pytest.mark.parametrize(
    ("payload", "content_type", "expected_status"),
    [
        (b"", "image/jpeg", 400),
        (b"image", "application/octet-stream", 415),
        (b"not a jpeg", "image/jpeg", 422),
        (b"x" * (2 * 1024 * 1024 + 1), "image/jpeg", 413),
    ],
)
def test_frame_endpoint_validates_type_size_and_image_data(
    frame_context,
    payload,
    content_type,
    expected_status,
):
    db, user, classroom, session = frame_context

    with pytest.raises(HTTPException) as error:
        post_frame(
            db,
            user,
            classroom,
            session,
            payload=payload,
            content_type=content_type,
        )

    assert error.value.status_code == expected_status


def test_frame_endpoint_rate_limits_per_authenticated_session(frame_context):
    db, user, classroom, session = frame_context

    first = post_frame(db, user, classroom, session)

    with pytest.raises(HTTPException) as limited:
        post_frame(db, user, classroom, session)

    assert first.detection_count == 1
    assert limited.value.status_code == 429
    assert limited.value.headers["Retry-After"]


def test_frame_endpoint_sanitizes_model_unavailable_error(
    frame_context,
    monkeypatch,
):
    db, user, classroom, session = frame_context

    class BrokenInferenceService:
        def analyze(self, _image):
            raise RuntimeError("internal model path and filesystem details")

    monkeypatch.setattr(
        frame_route, "frame_inference_service", BrokenInferenceService()
    )
    with pytest.raises(HTTPException) as unavailable:
        post_frame(db, user, classroom, session)

    assert unavailable.value.status_code == 503
    assert unavailable.value.detail == (
        "Person detection is unavailable. Check the configured model and retry."
    )
    assert "filesystem details" not in unavailable.value.detail


def test_frame_endpoint_reports_inference_timeout(frame_context, monkeypatch):
    db, user, classroom, session = frame_context

    async def slow_inference(_function, *_args):
        await asyncio.sleep(0.05)

    monkeypatch.setattr(frame_route, "FRAME_INFERENCE_TIMEOUT_SECONDS", 0.001)
    monkeypatch.setattr(frame_route, "run_in_threadpool", slow_inference)

    with pytest.raises(HTTPException) as timeout:
        post_frame(db, user, classroom, session)

    assert timeout.value.status_code == 504
    assert "timed out" in timeout.value.detail


def test_frame_inference_openapi_is_authenticated_and_documents_response():
    path = (
        f"{API_VERSION.rstrip('/')}/classrooms/"
        "{classroom_id}/sessions/{session_id}/frames"
    )
    operation = app.openapi()["paths"][path]["post"]

    assert operation["security"]
    assert operation["requestBody"]["content"]["image/jpeg"]["schema"] == {
        "type": "string",
        "format": "binary",
    }
    response_schema = app.openapi()["components"]["schemas"]["FrameInferenceResponse"]
    assert response_schema["properties"]["pipeline"]["type"] == "string"
    assert response_schema["properties"]["detections"]["type"] == "array"
    assert response_schema["properties"]["results_persisted"]["type"] == "boolean"
