from datetime import datetime

from pydantic import BaseModel, Field


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
    attendance_source: str | None = None


class AttentionHistoryResponse(BaseModel):
    id: int
    session_id: str
    student_id: str
    track_id: int | None
    attention_state: str | None
    confidence: float | None
    recorded_at: datetime


class HistoryStatisticsResponse(BaseModel):
    unique_students: int
    student_ids: list[str]
    attendance_records: int
    unassigned_attention_records: int = 0
    enrolled_students: int = 0
    present_students: int = 0
    absent_students: int = 0
    unknown_attendance_students: int = 0
    attendance_data_quality_students: int = 0
    unmarked_students: int = 0
    attention_records: int
    attentive_count: int
    not_attentive_count: int
    unknown_count: int
    partial_count: int = 0
    attentive_percentage: float
    not_attentive_percentage: float
    unknown_percentage: float
    partial_percentage: float = 0.0
    valid_attention_records: int = 0
    data_quality_records: int = 0
    attention_state_counts: dict[str, int] = Field(default_factory=dict)
    data_quality_state_counts: dict[str, int] = Field(default_factory=dict)


class SessionSummaryResponse(BaseModel):
    session: SessionHistoryResponse
    attendance: list[AttendanceHistoryResponse]
    attention: list[AttentionHistoryResponse]
    statistics: HistoryStatisticsResponse
