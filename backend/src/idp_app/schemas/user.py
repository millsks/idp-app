"""User Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


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
