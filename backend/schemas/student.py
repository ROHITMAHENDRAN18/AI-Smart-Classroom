from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class StudentBase(BaseModel):
    student_id: str
    name: str
    department: str
    year: int
    section: str
    email: EmailStr


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    year: int | None = None
    section: str | None = None
    email: EmailStr | None = None
    face_registered: bool | None = None


class StudentResponse(StudentBase):
    id: int
    face_registered: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudentUpdate(BaseModel):
    name: str
    department: str
    year: int
    section: str
    email: EmailStr