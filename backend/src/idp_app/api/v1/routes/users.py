"""User CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.core.database import get_db
from idp_app.core.security import get_current_user, hash_password
from idp_app.models.user import User
from idp_app.schemas.user import UserCreate, UserMe, UserMeUpdate, UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserMe, summary="Get current user profile")
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the authenticated user's own profile."""
    return current_user


@router.patch("/me", response_model=UserMe, summary="Update current user profile")
async def patch_me(
    user_in: UserMeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Update the authenticated user's display name."""
    current_user.full_name = user_in.full_name
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Register a new user account."""
    # Check for duplicate email / username
    existing = await db.execute(select(User).where((User.email == user_in.email) | (User.username == user_in.username)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        is_active=user_in.is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead, summary="Get user by ID")
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Retrieve a user by their numeric ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead, summary="Update user")
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Partially update a user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user
