from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassroomMemberCreateRequest(BaseModel):
    student_id: str


class ClassroomMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    classroom_id: int
    student_id: str
    joined_at: datetime
    is_active: bool