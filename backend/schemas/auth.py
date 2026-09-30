from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: str = Field(
        default="TEACHER",
        min_length=1,
        max_length=20,
    )


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=100,
    )

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    username: str
    email: str
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse