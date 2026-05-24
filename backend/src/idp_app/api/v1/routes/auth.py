"""Authentication endpoints (password login, GitHub OAuth, token exchange)."""

import logging
import secrets
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.core.config import Settings, get_settings
from idp_app.core.database import get_db, get_redis
from idp_app.core.security import create_access_token, verify_password
from idp_app.models.user import User
from idp_app.schemas.user import Token

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# GitHub OAuth constants
# ---------------------------------------------------------------------------
_GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
_GITHUB_SCOPES = "read:user user:email"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ExchangeTokenRequest(BaseModel):
    """Request body for the one-time OAuth exchange code endpoint."""

    exchange_code: str


# ---------------------------------------------------------------------------
# Password-based login
# ---------------------------------------------------------------------------


@router.post("/token", response_model=Token, summary="Obtain an access token (password)")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate with *username* and *password* and return a JWT access token."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


# ---------------------------------------------------------------------------
# GitHub OAuth — initiate
# ---------------------------------------------------------------------------


@router.get("/github", summary="Initiate GitHub OAuth login", response_class=RedirectResponse)
async def github_login(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Generate a CSRF state token, persist it in Redis, and redirect to GitHub."""
    state = secrets.token_urlsafe(32)
    await redis.set(f"oauth:state:{state}", "github", ex=300, nx=True)

    params = urlencode(
        {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
            "scope": _GITHUB_SCOPES,
            "state": state,
        }
    )
    logger.info(
        "OAuth login initiated",
        extra={"provider": "github", "success": True},
    )
    return RedirectResponse(url=f"{_GITHUB_AUTHORIZE_URL}?{params}")


# ---------------------------------------------------------------------------
# GitHub OAuth — callback
# ---------------------------------------------------------------------------


@router.get("/github/callback", summary="GitHub OAuth callback", response_class=RedirectResponse)
async def github_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
    settings: Annotated[Settings, Depends(get_settings)],
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """Validate state, exchange code, upsert user, issue JWT and redirect to frontend."""
    frontend_url = settings.FRONTEND_URL

    # 1. Provider-level error (e.g. user denied access).
    if error:
        logger.warning(
            "OAuth provider error",
            extra={"provider": "github", "success": False, "error_type": "provider_denied"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 2. Validate CSRF state token.
    if not state:
        logger.warning(
            "OAuth missing state parameter",
            extra={"provider": "github", "success": False, "error_type": "invalid_state"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    stored = await redis.get(f"oauth:state:{state}")
    if not stored:
        logger.warning(
            "OAuth invalid or expired state token",
            extra={"provider": "github", "success": False, "error_type": "invalid_state"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    # Single-use — delete immediately after validation.
    await redis.delete(f"oauth:state:{state}")

    # 3. Validate authorization code presence (GitHub normally includes `code`
    #    alongside `state`; guard against edge cases where it is absent).
    if not code:
        logger.warning(
            "OAuth callback missing code parameter",
            extra={"provider": "github", "success": False, "error_type": "provider_denied"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 4. Exchange authorization code for GitHub access token + fetch profile.
    try:
        async with httpx.AsyncClient() as http_client:
            token_response = await http_client.post(
                _GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
                },
                headers={"Accept": "application/json"},
            )
            token_data = token_response.json()
            github_access_token: str | None = token_data.get("access_token")
            if not github_access_token:
                raise ValueError(f"No access_token in GitHub response: {token_data}")

            auth_header = {"Authorization": f"token {github_access_token}", "Accept": "application/json"}

            profile_response = await http_client.get(_GITHUB_USER_URL, headers=auth_header)
            profile: dict[str, Any] = profile_response.json()

            # GitHub may return null email; fall back to the /user/emails endpoint.
            email: str | None = profile.get("email")
            if not email:
                emails_response = await http_client.get(_GITHUB_EMAILS_URL, headers=auth_header)
                for entry in emails_response.json():
                    if entry.get("primary") and entry.get("verified"):
                        email = entry["email"]
                        break

    except Exception:
        logger.exception(
            "OAuth token exchange failed",
            extra={"provider": "github", "success": False, "error_type": "exchange_failed"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 5. Validate profile identity field (guards against rate-limit / error responses).
    raw_id = profile.get("id")
    if raw_id is None:
        logger.warning(
            "OAuth profile missing id field",
            extra={"provider": "github", "success": False, "error_type": "exchange_failed"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")
    github_id = str(raw_id)

    # 6. Upsert user — keyed on (oauth_provider, oauth_provider_id).
    result = await db.execute(select(User).where(User.oauth_provider == "github", User.oauth_provider_id == github_id))
    user = result.scalar_one_or_none()

    if user is None:
        # First login: create new user record.
        # NOTE: email uniqueness is not explicitly guarded here — a password account
        # sharing the same email will cause an IntegrityError on db.flush().  A
        # proper fix (email-conflict detection + account linking) is tracked in
        # deferred-work.md and requires integration tests with a real database.
        candidate_username = str(profile.get("login") or f"github_{github_id}")
        existing_username = await db.execute(select(User).where(User.username == candidate_username))
        if existing_username.scalar_one_or_none():
            candidate_username = f"github_{github_id}"

        user = User(
            email=email or f"github_{github_id}@noemail.local",
            username=candidate_username,
            full_name=profile.get("name"),
            avatar_url=profile.get("avatar_url"),
            oauth_provider="github",
            oauth_provider_id=github_id,
            # Random token that is NOT a valid bcrypt hash — blocks password auth.
            hashed_password=secrets.token_hex(32),
        )
        db.add(user)
        await db.flush()
        logger.info(
            "OAuth new user created",
            extra={"provider": "github", "success": True, "user_id": user.id},
        )
    else:
        # Subsequent login: update mutable profile fields; never overwrite with None.
        new_name: str | None = profile.get("name")
        if new_name is not None:
            user.full_name = new_name
        if email:
            user.email = email
        new_avatar: str | None = profile.get("avatar_url")
        if new_avatar is not None:
            user.avatar_url = new_avatar
        logger.info(
            "OAuth existing user login",
            extra={"provider": "github", "success": True, "user_id": user.id},
        )

    # 7. Issue idp-app JWT and store behind a short-lived one-time exchange code.
    access_token = create_access_token(data={"sub": user.username})
    exchange_code = secrets.token_urlsafe(32)
    await redis.set(f"auth:exchange:{exchange_code}", access_token, ex=30)

    # 8. Redirect browser to frontend with exchange code.
    return RedirectResponse(url=f"{frontend_url}/auth/callback?exchange_code={exchange_code}")


# ---------------------------------------------------------------------------
# Token exchange — consume one-time code, return JWT
# ---------------------------------------------------------------------------


@router.post("/token/exchange", response_model=Token, summary="Exchange one-time code for JWT")
async def exchange_token(
    body: ExchangeTokenRequest,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
) -> Token:
    """Look up and consume a one-time OAuth exchange code, returning the JWT."""
    token: str | None = await redis.get(f"auth:exchange:{body.exchange_code}")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired exchange code",
        )
    await redis.delete(f"auth:exchange:{body.exchange_code}")
    return Token(access_token=token)


# ---------------------------------------------------------------------------
# Stateless logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_200_OK, summary="Logout (stateless)")
async def logout() -> dict[str, str]:
    """Stateless logout — the client is responsible for discarding the JWT."""
    return {"message": "Logged out successfully"}
