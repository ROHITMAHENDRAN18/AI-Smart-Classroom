from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ManualAttendanceEntry(BaseModel):
    student_id: str = Field(min_length=1, max_length=50)
    status: Literal["PRESENT", "ABSENT", "UNKNOWN"]


class ManualAttendanceRequest(BaseModel):
    records: list[ManualAttendanceEntry] = Field(min_length=1, max_length=200)


class ClassroomAttendanceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    student_id: str
    student_name: str | None
    status: str
    confidence: float | None
    recorded_at: datetime


class DailyAttendanceSummary(BaseModel):
    date: date
    total_records: int
    present_count: int
    absent_count: int
    unknown_count: int


class ClassroomAttendanceResponse(BaseModel):
    classroom_id: int
    from_date: date
    to_date: date
    generated_at: datetime
    total_records: int
    present_count: int
    absent_count: int
    unknown_count: int
    attendance_rate: float | None
    limit: int
    offset: int
    records: list[ClassroomAttendanceRecord]
    daily_trend: list[DailyAttendanceSummary]
