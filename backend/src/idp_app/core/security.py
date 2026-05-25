"""Password hashing and JWT token utilities."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.core.config import get_settings
from idp_app.core.database import get_db
from idp_app.models.user import User

settings = get_settings()

_password_hash = PasswordHash((BcryptHasher(),))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return bool(_password_hash.verify(plain_password, hashed_password))


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return str(_password_hash.hash(password))


def create_access_token(data: dict[str, str], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    The ``exp`` claim is stored as a Unix epoch integer as required by
    RFC 7519 §4.1.4 (NumericDate).
    """
    to_encode: dict[str, Any] = {**data}
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = int(expire.timestamp())  # NumericDate — must be an int
    return str(jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM))


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Raises :exc:`jwt.PyJWTError` if the token is invalid or expired.
    """
    payload: dict[str, Any] = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload


# ---------------------------------------------------------------------------
# OAuth2 scheme — token extracted from Authorization: Bearer <token> header
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """FastAPI dependency: decode Bearer JWT and return the matching User.

    Raises HTTP 401 if the token is missing, invalid, expired, or the user
    does not exist / is inactive.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
