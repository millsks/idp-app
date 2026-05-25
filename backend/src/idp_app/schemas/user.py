"""User Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Fields shared by all user schemas."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user (includes plain-text password)."""

    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for partially updating a user."""

    full_name: str | None = None
    is_active: bool | None = None


class UserMe(BaseModel):
    """Schema returned from GET /users/me — authenticated user's own profile."""

    id: int
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    oauth_provider: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMeUpdate(BaseModel):
    """Schema for PATCH /users/me — only display name is editable."""

    full_name: str = Field(min_length=1)

    @field_validator("full_name")
    @classmethod
    def strip_and_reject_whitespace(cls, v: str) -> str:
        """Strip surrounding whitespace; reject blank/whitespace-only values."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("full_name must not be blank or whitespace only")
        return stripped


class UserRead(UserBase):
    """Schema returned from the API (no password)."""

    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Payload extracted from a JWT token."""

    sub: str | None = None
