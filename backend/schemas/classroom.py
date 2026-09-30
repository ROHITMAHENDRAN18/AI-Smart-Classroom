from pydantic import BaseModel, ConfigDict, Field


class ClassroomCreateRequest(BaseModel):
    classroom_code: str = Field(
        min_length=2,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=150,
    )
    department: str = Field(
        min_length=2,
        max_length=100,
    )
    year: int = Field(
        ge=1,
        le=8,
    )
    section: str = Field(
        min_length=1,
        max_length=20,
    )


class ClassroomUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    department: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    year: int | None = Field(
        default=None,
        ge=1,
        le=8,
    )
    section: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )


class ClassroomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    classroom_code: str
    name: str
    department: str
    year: int
    section: str
    teacher_id: int
    is_active: bool