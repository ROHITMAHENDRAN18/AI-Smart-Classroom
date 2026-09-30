from datetime import datetime

from pydantic import BaseModel


class ClassroomOverviewStudent(BaseModel):
    student_id: str
    name: str
    department: str
    year: int
    section: str
    email: str | None
    face_registered: bool
    is_active: bool


class ClassroomOverviewSession(BaseModel):
    id: int
    session_id: str
    classroom_id: int
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    status: str
    created_at: datetime


class ClassroomOverviewResponse(BaseModel):
    classroom_id: int
    classroom_code: str
    classroom_name: str
    department: str
    year: int
    section: str
    teacher_id: int
    is_active: bool
    total_students: int
    active_students: int
    students: list[ClassroomOverviewStudent]
    active_session: ClassroomOverviewSession | None