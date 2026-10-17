from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PersonDetection(BaseModel):
    class_label: Literal["person"]
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    track_id: int | None = Field(default=None, ge=1)


class FaceDetection(BaseModel):
    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(gt=0)
    y2: int = Field(gt=0)
    confidence: float | None = None
    quality: Literal[
        "detected_unscored",
        "embedding_available",
        "embedding_unavailable",
    ]
    student_id: str | None = None
    identity: str = "Unknown"
    similarity: float | None = Field(default=None, ge=-1, le=1)
    recognition_status: Literal[
        "recognized",
        "unknown",
        "unavailable",
    ] = "unavailable"
    head_pose: dict | None = None
    eye_state: Literal["OPEN", "CLOSED", "PARTIAL", "UNKNOWN"] = "UNKNOWN"
    attention_state: Literal["ATTENTIVE", "PARTIAL", "NOT ATTENTIVE", "UNKNOWN"] = "UNKNOWN"
    attention_score: float | None = Field(default=None, ge=0, le=1)
    attention_confidence: float = Field(default=0, ge=0, le=1)


class FeatureAvailability(BaseModel):
    status: Literal["available", "not_connected", "error"]
    detail: str


class InferenceFeatureStatuses(BaseModel):
    person_detection: FeatureAvailability
    result_persistence: FeatureAvailability
    face_detection: FeatureAvailability
    face_recognition: FeatureAvailability
    tracking: FeatureAvailability
    attention_estimation: FeatureAvailability
    head_pose_estimation: FeatureAvailability
    eye_state_estimation: FeatureAvailability
    attention_persistence: FeatureAvailability
    attendance: FeatureAvailability


class FrameInferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    classroom_id: int
    frame_received_at: datetime
    processed_at: datetime
    frame_width: int
    frame_height: int
    processing_status: Literal["completed"]
    inference_duration_ms: float = Field(ge=0)
    pipeline: Literal["person_detection"]
    attention_inference: Literal["available", "partial", "unknown", "not_connected", "error"]
    attention_state: Literal["ATTENTIVE", "PARTIAL", "NOT ATTENTIVE", "UNKNOWN"] = "UNKNOWN"
    attention_score: float | None = Field(default=None, ge=0, le=1)
    attention_confidence: float = Field(default=0, ge=0, le=1)
    head_pose: Literal["FRONT", "LEFT", "RIGHT", "UP", "DOWN", "UNKNOWN"] = "UNKNOWN"
    features: InferenceFeatureStatuses
    detections: list[PersonDetection]
    face_detections: list[FaceDetection] = Field(default_factory=list)
    detection_count: int
    results_persisted: bool


class FrameInferenceSummaryResponse(FrameInferenceResponse):
    frames_processed: int = Field(ge=1)
    unknown_detections: int = Field(ge=0)
    updated_at: datetime
