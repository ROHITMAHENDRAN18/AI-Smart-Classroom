from pydantic import BaseModel
from typing import Optional


class AttendanceAnalyticsResponse(BaseModel):
    student_id: str
    total_sessions: int
    attended_sessions: int
    attendance_percentage: float


class AttentionAnalyticsResponse(BaseModel):
    student_id: str
    total_records: int
    attentive_records: int
    partial_records: int
    not_attentive_records: int
    unknown_records: int
    average_attention_score: float
    attention_percentage: float


class StudentAnalyticsResponse(BaseModel):
    student_id: str
    student_name: Optional[str]
    attendance: AttendanceAnalyticsResponse
    attention: AttentionAnalyticsResponse