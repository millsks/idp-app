"""Authentication endpoints (password login, GitHub OAuth, Google OAuth, token exchange)."""

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
# Google OAuth constants
# ---------------------------------------------------------------------------
_GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://openid.googleapis.com/v1/userinfo"
_GOOGLE_SCOPES = "openid email profile"

# ---------------------------------------------------------------------------
# Shared HTTP header constants
# ---------------------------------------------------------------------------
_ACCEPT_JSON = "application/json"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ExchangeTokenRequest(BaseModel):
    """Request body for the one-time OAuth exchange code endpoint."""

    exchange_code: str


# ---------------------------------------------------------------------------
# Shared OAuth helper
# ---------------------------------------------------------------------------


async def _resolve_unique_username(
    db: AsyncSession,
    hint: str,
    provider: str,
    provider_id: str,
) -> str:
    """Return a username that doesn't already exist in the database.

    Tries ``hint`` first, then ``hint1`` … ``hint9``, then falls back to
    ``{provider}_{provider_id}`` as an always-unique last resort.
    """
    check = await db.execute(select(User).where(User.username == hint))
    if check.scalar_one_or_none() is None:
        return hint

    for suffix in range(1, 10):
        candidate = f"{hint}{suffix}"
        check = await db.execute(select(User).where(User.username == candidate))
        if check.scalar_one_or_none() is None:
            return candidate

    return f"{provider}_{provider_id}"


async def _upsert_oauth_user(
    db: AsyncSession,
    *,
    provider: str,
    provider_id: str,
    email: str | None,
    full_name: str | None,
    avatar_url: str | None,
    username_hint: str,
) -> User:
    """Find or create an OAuth-authenticated user keyed on (oauth_provider, oauth_provider_id).

    On first login a new User is created using a unique username resolved from
    ``username_hint``.  On subsequent logins mutable profile fields are updated
    in-place (``None`` values are never written — they don't overwrite existing data).

    Note: lookup is intentionally **only** by (provider, provider_id) — never by
    email.  Two accounts with the same email under different providers are
    legitimate separate records in MVP1 (AC-6).
    """
    result = await db.execute(
        select(User).where(
            User.oauth_provider == provider,
            User.oauth_provider_id == provider_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        username = await _resolve_unique_username(db, username_hint, provider, provider_id)
        user = User(
            email=email or f"{provider}_{provider_id}@noemail.local",
            username=username,
            full_name=full_name,
            avatar_url=avatar_url,
            oauth_provider=provider,
            oauth_provider_id=provider_id,
            # Random token that is NOT a valid bcrypt hash — blocks password auth.
            hashed_password=secrets.token_hex(32),
        )
        db.add(user)
        await db.flush()
        logger.info(
            "OAuth new user created",
            extra={"provider": provider, "success": True, "user_id": user.id},
        )
    else:
        # Subsequent login: update mutable profile fields; never overwrite with None.
        if full_name is not None:
            user.full_name = full_name
        if email:
            user.email = email
        if avatar_url is not None:
            user.avatar_url = avatar_url
        logger.info(
            "OAuth existing user login",
            extra={"provider": provider, "success": True, "user_id": user.id},
        )

    return user


def _oauth_state_matches_provider(stored: str | bytes | None, expected_provider: str) -> bool:
    """Return True when stored OAuth state value matches the expected provider."""
    if stored is None:
        return False
    if isinstance(stored, bytes):
        stored = stored.decode("utf-8", errors="ignore")
    return stored == expected_provider


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
    if not _oauth_state_matches_provider(stored, "github"):
        logger.warning(
            "OAuth invalid or expired state token",
            extra={"provider": "github", "success": False, "error_type": "invalid_state"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    # Single-use — delete immediately after validation.
    await redis.delete(f"oauth:state:{state}")

    # 3. Validate authorization code presence.
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
                headers={"Accept": _ACCEPT_JSON},
            )
            token_data = token_response.json()
            github_access_token: str | None = token_data.get("access_token")
            if not github_access_token:
                raise ValueError(f"No access_token in GitHub response: {token_data}")

            auth_header = {"Authorization": f"token {github_access_token}", "Accept": _ACCEPT_JSON}

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

    # 5. Validate profile identity field.
    raw_id = profile.get("id")
    if raw_id is None:
        logger.warning(
            "OAuth profile missing id field",
            extra={"provider": "github", "success": False, "error_type": "exchange_failed"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")
    github_id = str(raw_id)

    # 6. Upsert user — keyed on (oauth_provider, oauth_provider_id).
    username_hint = str(profile.get("login") or f"github_{github_id}")
    user = await _upsert_oauth_user(
        db,
        provider="github",
        provider_id=github_id,
        email=email,
        full_name=profile.get("name"),
        avatar_url=profile.get("avatar_url"),
        username_hint=username_hint,
    )

    # 7. Issue idp-app JWT and store behind a short-lived one-time exchange code.
    access_token = create_access_token(data={"sub": user.username})
    exchange_code = secrets.token_urlsafe(32)
    await redis.set(f"auth:exchange:{exchange_code}", access_token, ex=30)

    # 8. Redirect browser to frontend with exchange code.
    return RedirectResponse(url=f"{frontend_url}/auth/callback?exchange_code={exchange_code}")


# ---------------------------------------------------------------------------
# Google OAuth — initiate
# ---------------------------------------------------------------------------


@router.get("/google", summary="Initiate Google OAuth login", response_class=RedirectResponse)
async def google_login(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Generate a CSRF state token, persist it in Redis, and redirect to Google's OAuth consent page."""
    state = secrets.token_urlsafe(32)
    await redis.set(f"oauth:state:{state}", "google", ex=300, nx=True)

    params = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": _GOOGLE_SCOPES,
            "state": state,
            "access_type": "online",
        }
    )
    logger.info(
        "OAuth login initiated",
        extra={"provider": "google", "success": True},
    )
    return RedirectResponse(url=f"{_GOOGLE_AUTHORIZE_URL}?{params}")


# ---------------------------------------------------------------------------
# Google OAuth — callback
# ---------------------------------------------------------------------------


@router.get("/google/callback", summary="Google OAuth callback", response_class=RedirectResponse)
async def google_callback(
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
            extra={"provider": "google", "success": False, "error_type": "provider_denied"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 2. Validate CSRF state token.
    if not state:
        logger.warning(
            "OAuth missing state parameter",
            extra={"provider": "google", "success": False, "error_type": "invalid_state"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    stored = await redis.get(f"oauth:state:{state}")
    if not _oauth_state_matches_provider(stored, "google"):
        logger.warning(
            "OAuth invalid or expired state token",
            extra={"provider": "google", "success": False, "error_type": "invalid_state"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    # Single-use — delete immediately after validation.
    await redis.delete(f"oauth:state:{state}")

    # 3. Validate authorization code presence.
    if not code:
        logger.warning(
            "OAuth callback missing code parameter",
            extra={"provider": "google", "success": False, "error_type": "provider_denied"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 4. Exchange authorization code for Google access token + fetch userinfo.
    try:
        async with httpx.AsyncClient() as http_client:
            token_response = await http_client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": _ACCEPT_JSON},
            )
            token_data = token_response.json()
            google_access_token: str | None = token_data.get("access_token")
            if not google_access_token:
                raise ValueError(f"No access_token in Google response: {token_data}")

            userinfo_response = await http_client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )
            userinfo: dict[str, Any] = userinfo_response.json()

    except Exception:
        logger.exception(
            "OAuth token exchange failed",
            extra={"provider": "google", "success": False, "error_type": "exchange_failed"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 5. Validate the stable identity field (sub).
    google_sub: str | None = userinfo.get("sub")
    if not google_sub:
        logger.warning(
            "OAuth profile missing sub field",
            extra={"provider": "google", "success": False, "error_type": "exchange_failed"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=provider_denied")

    # 6. Derive username from email prefix; fall back to google_{sub} if no email.
    google_email: str | None = userinfo.get("email")
    if google_email:
        username_hint = google_email.split("@")[0]
    else:
        username_hint = f"google_{google_sub}"

    # 7. Upsert user — keyed on (oauth_provider, oauth_provider_id = sub).
    #    AC-6: lookup is ONLY by (provider, sub) — never by email.
    user = await _upsert_oauth_user(
        db,
        provider="google",
        provider_id=google_sub,
        email=google_email,
        full_name=userinfo.get("name"),
        avatar_url=userinfo.get("picture"),
        username_hint=username_hint,
    )

    # 8. Issue idp-app JWT and store behind a short-lived one-time exchange code.
    access_token = create_access_token(data={"sub": user.username})
    exchange_code = secrets.token_urlsafe(32)
    await redis.set(f"auth:exchange:{exchange_code}", access_token, ex=30)

    # 9. Redirect browser to frontend with exchange code.
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
