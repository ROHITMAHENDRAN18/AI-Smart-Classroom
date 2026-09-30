from pydantic import BaseModel, ConfigDict, Field


class TeacherCreateRequest(BaseModel):
    teacher_id: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    department: str = Field(min_length=2, max_length=100)
    designation: str = Field(
        default="Teacher",
        min_length=2,
        max_length=100,
    )


class TeacherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    teacher_id: str
    name: str
    department: str
    designation: str