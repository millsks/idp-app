"""Password hashing and JWT token utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from idp_app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return bool(pwd_context.verify(plain_password, hashed_password))


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return str(pwd_context.hash(password))


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

    Raises :exc:`jose.JWTError` if the token is invalid or expired.
    """
    payload: dict[str, Any] = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload
