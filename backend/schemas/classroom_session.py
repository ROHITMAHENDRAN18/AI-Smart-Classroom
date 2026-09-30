from datetime import datetime

from pydantic import BaseModel


class ClassroomSessionResponse(BaseModel):
    id: int
    session_id: str
    classroom_id: int
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    status: str
    created_at: datetime


class SessionStartResponse(BaseModel):
    session: ClassroomSessionResponse


class SessionStopResponse(BaseModel):
    session: ClassroomSessionResponse