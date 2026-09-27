from datetime import datetime

from pydantic import BaseModel


class SessionHistoryResponse(BaseModel):
    id: int
    session_id: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    status: str
    created_at: datetime


class AttendanceHistoryResponse(BaseModel):
    id: int
    session_id: str
    student_id: str
    status: str
    confidence: float | None
    recorded_at: datetime


class AttentionHistoryResponse(BaseModel):
    id: int
    session_id: str
    student_id: str
    track_id: int | None
    attention_state: str
    confidence: float | None
    recorded_at: datetime


class HistoryStatisticsResponse(BaseModel):
    unique_students: int
    student_ids: list[str]
    attendance_records: int
    attention_records: int
    attentive_count: int
    not_attentive_count: int
    unknown_count: int
    attentive_percentage: float
    not_attentive_percentage: float
    unknown_percentage: float


class SessionSummaryResponse(BaseModel):
    session: SessionHistoryResponse
    attendance: list[AttendanceHistoryResponse]
    attention: list[AttentionHistoryResponse]
    statistics: HistoryStatisticsResponse