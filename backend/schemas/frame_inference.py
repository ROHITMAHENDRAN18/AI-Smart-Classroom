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


class FeatureAvailability(BaseModel):
    status: Literal["available", "not_connected"]
    detail: str


class InferenceFeatureStatuses(BaseModel):
    person_detection: FeatureAvailability
    face_detection: FeatureAvailability
    face_recognition: FeatureAvailability
    tracking: FeatureAvailability
    attention_estimation: FeatureAvailability
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
    attention_inference: Literal["not_connected"]
    features: InferenceFeatureStatuses
    detections: list[PersonDetection]
    detection_count: int
    results_persisted: bool
