from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class StudentCreateRequest(BaseModel):
    student_id: str = Field(
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

    email: EmailStr | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class StudentUpdateRequest(BaseModel):
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

    email: EmailStr | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class StudentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    student_id: str
    name: str
    department: str
    year: int
    section: str
    email: str | None
    face_registered: bool
    classroom_is_active: bool | None = None