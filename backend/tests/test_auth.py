"""Tests for the /api/v1/auth endpoints."""

import secrets
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.models.user import User
from tests.conftest import FakeRedis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_github_http(
    access_token: str = "ghtoken123",
    profile: dict[str, object] | None = None,
    emails: list[dict[str, object]] | None = None,
) -> MagicMock:
    """Return a configured mock for httpx.AsyncClient used in OAuth callbacks."""
    if profile is None:
        profile = {
            "id": 99001,
            "login": "octocat",
            "name": "Octo Cat",
            "email": "octocat@example.com",
            "avatar_url": "https://avatars.github.com/u/99001",
        }

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(json=MagicMock(return_value={"access_token": access_token}))
    mock_http.get.return_value = MagicMock(json=MagicMock(return_value=profile))
    return mock_http


def _patch_httpx(mock_http: AsyncMock) -> MagicMock:
    """Context-manager patch that replaces httpx.AsyncClient with mock_http."""
    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_cls


# ---------------------------------------------------------------------------
# Password login (existing tests, kept intact)
# ---------------------------------------------------------------------------


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict[str, object]:
    """Register a user for auth tests."""
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "authuser@example.com",
            "username": "authuser",
            "password": "authpassword1",
        },
    )
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


class TestLogin:
    async def test_login_success_returns_token(self, client: AsyncClient, registered_user: dict[str, object]) -> None:
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "authuser", "password": "authpassword1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, registered_user: dict[str, object]
    ) -> None:
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "authuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_unknown_user_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "doesntmatter"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GitHub OAuth — initiate
# ---------------------------------------------------------------------------


class TestGitHubOAuthInitiate:
    async def test_github_login_redirects_to_github(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/github", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "github.com/login/oauth/authorize" in location

    async def test_github_login_includes_state_param(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/github", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "state=" in location

    async def test_github_login_stores_state_in_redis(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        from urllib.parse import parse_qs, urlparse

        response = await client.get("/api/v1/auth/github", follow_redirects=False)
        location = response.headers["location"]
        state = parse_qs(urlparse(location).query)["state"][0]
        assert await fake_redis.get(f"oauth:state:{state}") == "github"

    async def test_github_login_includes_required_scopes(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/github", follow_redirects=False)
        location = response.headers["location"]
        assert "read%3Auser" in location or "read:user" in location.replace("%3A", ":")


# ---------------------------------------------------------------------------
# GitHub OAuth — callback error paths
# ---------------------------------------------------------------------------


class TestGitHubCallbackErrors:
    async def test_missing_state_redirects_invalid_state(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get(
            "/api/v1/auth/github/callback?code=someauthcode",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "invalid_state" in response.headers["location"]

    async def test_invalid_state_token_redirects(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get(
            "/api/v1/auth/github/callback?code=someauthcode&state=notarealtokenatall",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "invalid_state" in response.headers["location"]

    async def test_provider_error_redirects_provider_denied(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get(
            "/api/v1/auth/github/callback?error=access_denied",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "provider_denied" in response.headers["location"]

    async def test_state_for_other_provider_redirects_invalid_state(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        """State token created for Google must be rejected by GitHub callback."""
        await fake_redis.set("oauth:state:cross-provider", "google", ex=300)

        response = await client.get(
            "/api/v1/auth/github/callback?code=someauthcode&state=cross-provider",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "invalid_state" in response.headers["location"]
        assert await fake_redis.get("oauth:state:cross-provider") == "google"

    async def test_state_is_single_use(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        """Using a state value twice must fail on the second attempt."""
        await fake_redis.set("oauth:state:onetime", "github", ex=300)

        mock_http = _mock_github_http()
        mock_cls = _patch_httpx(mock_http)

        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", mock_cls):
            # First callback — succeeds (or at least consumes state)
            await client.get(
                "/api/v1/auth/github/callback?code=c1&state=onetime",
                follow_redirects=False,
            )

        # State must be gone now
        assert await fake_redis.get("oauth:state:onetime") is None

        # Second callback — no state in Redis → invalid_state redirect
        response2 = await client.get(
            "/api/v1/auth/github/callback?code=c2&state=onetime",
            follow_redirects=False,
        )
        assert "invalid_state" in response2.headers["location"]


# ---------------------------------------------------------------------------
# GitHub OAuth — happy-path callback
# ---------------------------------------------------------------------------


class TestGitHubCallbackSuccess:
    async def test_first_login_creates_user(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        await fake_redis.set("oauth:state:state_first", "github", ex=300)

        mock_http = _mock_github_http(
            profile={
                "id": 42001,
                "login": "newuser",
                "name": "New User",
                "email": "newuser@example.com",
                "avatar_url": "https://avatars.github.com/u/42001",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/github/callback?code=authcode&state=state_first",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "/auth/callback?exchange_code=" in response.headers["location"]

        result = await db_session.execute(
            select(User).where(User.oauth_provider == "github", User.oauth_provider_id == "42001")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.full_name == "New User"
        assert user.email == "newuser@example.com"
        assert user.avatar_url == "https://avatars.github.com/u/42001"
        assert user.oauth_provider == "github"
        assert user.username == "newuser"

    async def test_return_login_updates_profile(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        # Pre-existing user
        existing = User(
            email="existing@example.com",
            username="existing_octocat",
            full_name="Old Name",
            avatar_url="https://old.avatar.url",
            oauth_provider="github",
            oauth_provider_id="55001",
            hashed_password=secrets.token_hex(32),
        )
        db_session.add(existing)
        await db_session.flush()

        await fake_redis.set("oauth:state:state_return", "github", ex=300)

        mock_http = _mock_github_http(
            profile={
                "id": 55001,
                "login": "existing_octocat",
                "name": "Updated Name",
                "email": "updated@example.com",
                "avatar_url": "https://new.avatar.url",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/github/callback?code=authcode&state=state_return",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)

        # The route handler and test share the same session (test override).
        # The identity-map object is mutated in-place by the route — no refresh needed.
        assert existing.full_name == "Updated Name"
        assert existing.email == "updated@example.com"
        assert existing.avatar_url == "https://new.avatar.url"

    async def test_null_profile_email_falls_back_to_emails_endpoint(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """When GitHub profile has no email, the /user/emails endpoint is called."""
        await fake_redis.set("oauth:state:state_noemail", "github", ex=300)

        mock_http = AsyncMock()
        mock_http.post.return_value = MagicMock(json=MagicMock(return_value={"access_token": "tok"}))

        profile_mock = MagicMock(
            json=MagicMock(
                return_value={
                    "id": 77001,
                    "login": "noemail_user",
                    "name": "No Email User",
                    "email": None,
                    "avatar_url": "https://avatars.github.com/u/77001",
                }
            )
        )
        emails_mock = MagicMock(
            json=MagicMock(
                return_value=[
                    {"email": "private@example.com", "primary": True, "verified": True},
                ]
            )
        )
        mock_http.get.side_effect = [profile_mock, emails_mock]

        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/github/callback?code=authcode&state=state_noemail",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)

        result = await db_session.execute(select(User).where(User.oauth_provider_id == "77001"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == "private@example.com"

    async def test_exchange_code_stored_in_redis(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        from urllib.parse import parse_qs, urlparse

        await fake_redis.set("oauth:state:state_exchange_test", "github", ex=300)

        mock_http = _mock_github_http(
            profile={"id": 88001, "login": "exchuser", "name": "X", "email": "x@x.com", "avatar_url": ""}
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/github/callback?code=authcode&state=state_exchange_test",
                follow_redirects=False,
            )

        location = response.headers["location"]
        exchange_code = parse_qs(urlparse(location).query)["exchange_code"][0]
        stored_jwt = await fake_redis.get(f"auth:exchange:{exchange_code}")
        assert stored_jwt is not None
        assert len(stored_jwt) > 10  # non-empty JWT string

    async def test_return_login_does_not_overwrite_with_none(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """Provider returning null full_name/avatar_url must not erase existing values."""
        existing = User(
            email="stable@example.com",
            username="stable_user",
            full_name="Keep This Name",
            avatar_url="https://keep.this.avatar.url",
            oauth_provider="github",
            oauth_provider_id="66001",
            hashed_password=secrets.token_hex(32),
        )
        db_session.add(existing)
        await db_session.flush()

        await fake_redis.set("oauth:state:state_nullprofile", "github", ex=300)

        mock_http = _mock_github_http(
            profile={
                "id": 66001,
                "login": "stable_user",
                "name": None,  # provider returned null name
                "email": "stable@example.com",
                "avatar_url": None,  # provider returned null avatar
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/github/callback?code=authcode&state=state_nullprofile",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        # Existing values must be preserved
        assert existing.full_name == "Keep This Name"
        assert existing.avatar_url == "https://keep.this.avatar.url"

    async def test_missing_profile_id_redirects_provider_denied(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        """GitHub error response without id field (e.g. rate-limit) → provider_denied redirect."""
        await fake_redis.set("oauth:state:state_noid", "github", ex=300)

        mock_http = _mock_github_http(
            profile={
                "message": "API rate limit exceeded",
                # no 'id' key
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/github/callback?code=authcode&state=state_noid",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "provider_denied" in response.headers["location"]


# ---------------------------------------------------------------------------
# Token exchange endpoint
# ---------------------------------------------------------------------------


class TestTokenExchange:
    async def test_valid_exchange_code_returns_token(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        await fake_redis.set("auth:exchange:mycode123", "myjwttoken.header.sig", ex=30)

        response = await client.post(
            "/api/v1/auth/token/exchange",
            json={"exchange_code": "mycode123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "myjwttoken.header.sig"
        assert data["token_type"] == "bearer"

    async def test_valid_exchange_code_is_single_use(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        await fake_redis.set("auth:exchange:singleuse", "sometoken", ex=30)

        await client.post("/api/v1/auth/token/exchange", json={"exchange_code": "singleuse"})

        # Code must be deleted after first use
        assert await fake_redis.get("auth:exchange:singleuse") is None

        # Second attempt must fail
        response2 = await client.post("/api/v1/auth/token/exchange", json={"exchange_code": "singleuse"})
        assert response2.status_code == 400

    async def test_invalid_exchange_code_returns_400(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.post(
            "/api/v1/auth/token/exchange",
            json={"exchange_code": "doesnotexist"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_logout_returns_200(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Google OAuth helpers
# ---------------------------------------------------------------------------


def _mock_google_http(
    access_token: str = "google-access-token",
    userinfo: dict[str, object] | None = None,
) -> MagicMock:
    """Return a configured mock for httpx.AsyncClient used in Google OAuth callbacks."""
    if userinfo is None:
        userinfo = {
            "sub": "google-sub-12345",
            "email": "guser@example.com",
            "name": "Google User",
            "picture": "https://lh3.googleusercontent.com/photo.jpg",
        }

    mock_http = AsyncMock()
    mock_http.post.return_value = MagicMock(json=MagicMock(return_value={"access_token": access_token}))
    mock_http.get.return_value = MagicMock(json=MagicMock(return_value=userinfo))
    return mock_http


# ---------------------------------------------------------------------------
# Google OAuth — initiate
# ---------------------------------------------------------------------------


class TestGoogleOAuthInitiate:
    async def test_google_login_redirects_to_google(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/google", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "accounts.google.com/o/oauth2/v2/auth" in location

    async def test_google_login_includes_state_param(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/google", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "state=" in location

    async def test_google_login_stores_state_in_redis(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/google", follow_redirects=False)
        location = response.headers["location"]
        state = parse_qs(urlparse(location).query)["state"][0]
        assert await fake_redis.get(f"oauth:state:{state}") == "google"

    async def test_google_login_includes_openid_scope(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get("/api/v1/auth/google", follow_redirects=False)
        location = response.headers["location"]
        decoded = location.replace("%20", " ").replace("+", " ")
        assert "openid" in decoded
        assert "email" in decoded
        assert "profile" in decoded


# ---------------------------------------------------------------------------
# Google OAuth — callback error paths
# ---------------------------------------------------------------------------


class TestGoogleCallbackErrors:
    async def test_missing_state_redirects_invalid_state(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get(
            "/api/v1/auth/google/callback?code=someauthcode",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "invalid_state" in response.headers["location"]

    async def test_invalid_state_token_redirects(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get(
            "/api/v1/auth/google/callback?code=someauthcode&state=notarealtokenatall",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "invalid_state" in response.headers["location"]

    async def test_provider_error_redirects_provider_denied(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        response = await client.get(
            "/api/v1/auth/google/callback?error=access_denied",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "provider_denied" in response.headers["location"]

    async def test_state_for_other_provider_redirects_invalid_state(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        """State token created for GitHub must be rejected by Google callback."""
        await fake_redis.set("oauth:state:cross-provider", "github", ex=300)

        response = await client.get(
            "/api/v1/auth/google/callback?code=someauthcode&state=cross-provider",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        assert "invalid_state" in response.headers["location"]
        assert await fake_redis.get("oauth:state:cross-provider") == "github"

    async def test_state_is_single_use(self, client: AsyncClient, fake_redis: FakeRedis) -> None:
        """Using a state value twice must fail on the second attempt."""
        await fake_redis.set("oauth:state:google-onetime", "google", ex=300)

        mock_http = _mock_google_http()
        mock_cls = _patch_httpx(mock_http)

        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", mock_cls):
            await client.get(
                "/api/v1/auth/google/callback?code=c1&state=google-onetime",
                follow_redirects=False,
            )

        # State must be consumed after first use
        assert await fake_redis.get("oauth:state:google-onetime") is None

        response2 = await client.get(
            "/api/v1/auth/google/callback?code=c2&state=google-onetime",
            follow_redirects=False,
        )
        assert "invalid_state" in response2.headers["location"]

    async def test_missing_sub_in_userinfo_redirects_provider_denied(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        """Google userinfo without sub field (e.g. error response) → provider_denied redirect."""
        await fake_redis.set("oauth:state:google-nosub", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={"error": "invalid_token"},  # no 'sub' key
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-nosub",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "provider_denied" in response.headers["location"]


# ---------------------------------------------------------------------------
# Google OAuth — happy-path callback
# ---------------------------------------------------------------------------


class TestGoogleCallbackSuccess:
    async def test_first_login_creates_user(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """First Google login creates a new user record (AC-3)."""
        await fake_redis.set("oauth:state:google-state-first", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-first-001",
                "email": "firstlogin@example.com",
                "name": "First Login User",
                "picture": "https://lh3.googleusercontent.com/first.jpg",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-first",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "/auth/callback?exchange_code=" in response.headers["location"]

        result = await db_session.execute(
            select(User).where(User.oauth_provider == "google", User.oauth_provider_id == "google-sub-first-001")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.full_name == "First Login User"
        assert user.email == "firstlogin@example.com"
        assert user.avatar_url == "https://lh3.googleusercontent.com/first.jpg"
        assert user.oauth_provider == "google"
        assert user.username == "firstlogin"  # derived from email prefix

    async def test_first_login_sets_random_hashed_password(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """New Google user's hashed_password is a random token, not a valid bcrypt hash (AC-3)."""
        await fake_redis.set("oauth:state:google-state-pw", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-pw-001",
                "email": "pwcheck@example.com",
                "name": "PW Check",
                "picture": "",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-pw",
                follow_redirects=False,
            )

        result = await db_session.execute(select(User).where(User.oauth_provider_id == "google-sub-pw-001"))
        user = result.scalar_one_or_none()
        assert user is not None
        # hashed_password must be set but NOT a valid bcrypt hash (which starts with "$2b$")
        assert user.hashed_password
        assert not user.hashed_password.startswith("$2b$")

    async def test_return_login_updates_profile(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """Subsequent Google login updates full_name, email, avatar_url (AC-4)."""
        existing = User(
            email="old-google@example.com",
            username="old_google_user",
            full_name="Old Google Name",
            avatar_url="https://old-google.avatar.url",
            oauth_provider="google",
            oauth_provider_id="google-sub-return-001",
            hashed_password=secrets.token_hex(32),
        )
        db_session.add(existing)
        await db_session.flush()

        await fake_redis.set("oauth:state:google-state-return", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-return-001",
                "email": "updated-google@example.com",
                "name": "Updated Google Name",
                "picture": "https://new-google.avatar.url",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-return",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)

        # The route and test share the same session — mutations are visible in-place.
        assert existing.full_name == "Updated Google Name"
        assert existing.email == "updated-google@example.com"
        assert existing.avatar_url == "https://new-google.avatar.url"

    async def test_return_login_does_not_overwrite_with_none(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """Provider returning null name/picture must not erase existing values."""
        existing = User(
            email="stable-google@example.com",
            username="stable_google_user",
            full_name="Stable Google Name",
            avatar_url="https://stable-google.avatar.url",
            oauth_provider="google",
            oauth_provider_id="google-sub-stable-001",
            hashed_password=secrets.token_hex(32),
        )
        db_session.add(existing)
        await db_session.flush()

        await fake_redis.set("oauth:state:google-state-stable", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-stable-001",
                "email": "stable-google@example.com",
                "name": None,  # provider returned null name
                "picture": None,  # provider returned null picture
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-stable",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert existing.full_name == "Stable Google Name"
        assert existing.avatar_url == "https://stable-google.avatar.url"

    async def test_no_merge_when_same_email_different_provider(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """AC-6: A Google login does NOT merge with an existing account from another provider.

        The lookup is performed exclusively by (oauth_provider, oauth_provider_id).
        Even when two provider accounts belong to the "same person", they remain
        distinct user records in MVP1 — no email-based merge occurs.

        This test validates the same-email case explicitly.
        """
        # Pre-existing GitHub user
        github_user = User(
            email="alice@example.com",
            username="alice_github",
            full_name="Alice via GitHub",
            avatar_url="https://github.avatar.url/alice",
            oauth_provider="github",
            oauth_provider_id="github-id-nomerge-001",
            hashed_password=secrets.token_hex(32),
        )
        db_session.add(github_user)
        await db_session.flush()

        await fake_redis.set("oauth:state:google-state-nomerge", "google", ex=300)

        # Google login with the same email address
        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-nomerge-001",
                "email": "alice@example.com",
                "name": "Alice via Google",
                "picture": "https://google.avatar.url/alice",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-nomerge",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "/auth/callback?exchange_code=" in response.headers["location"]

        # A separate Google user record must exist alongside the GitHub one
        google_result = await db_session.execute(
            select(User).where(User.oauth_provider == "google", User.oauth_provider_id == "google-sub-nomerge-001")
        )
        google_user = google_result.scalar_one_or_none()
        assert google_user is not None, "Google user record was not created"
        assert google_user.oauth_provider == "google"
        assert google_user.email == "alice@example.com"

        # The GitHub user must be completely untouched
        github_result = await db_session.execute(
            select(User).where(User.oauth_provider == "github", User.oauth_provider_id == "github-id-nomerge-001")
        )
        github_still = github_result.scalar_one_or_none()
        assert github_still is not None, "GitHub user was unexpectedly removed"
        assert github_still.oauth_provider == "github"
        assert github_still.email == "alice@example.com"

        # Two distinct records — no merge
        assert google_user.id != github_still.id

    async def test_exchange_code_stored_in_redis(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        """Successful Google callback stores a one-time exchange code in Redis (AC-5)."""
        await fake_redis.set("oauth:state:google-state-exchtest", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-exch-001",
                "email": "exchtest@example.com",
                "name": "Exch Test",
                "picture": "",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-exchtest",
                follow_redirects=False,
            )

        location = response.headers["location"]
        exchange_code = parse_qs(urlparse(location).query)["exchange_code"][0]
        stored_jwt = await fake_redis.get(f"auth:exchange:{exchange_code}")
        assert stored_jwt is not None
        assert len(stored_jwt) > 10  # non-empty JWT string

    async def test_username_derived_from_email_prefix(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """Google user's username is derived from the email prefix (AC-3)."""
        await fake_redis.set("oauth:state:google-state-uname", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-uname-001",
                "email": "johndoe@company.org",
                "name": "John Doe",
                "picture": "",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-uname",
                follow_redirects=False,
            )

        result = await db_session.execute(select(User).where(User.oauth_provider_id == "google-sub-uname-001"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.username == "johndoe"

    async def test_username_numeric_suffix_when_hint_taken(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """When email-prefix username is taken, a numeric suffix is appended (AC-3 / Dev Notes)."""
        # Pre-occupy the plain "alice" username
        existing = User(
            email="alice-other@example.com",
            username="alice",
            full_name="Other Alice",
            oauth_provider="github",
            oauth_provider_id="github-alice-001",
            hashed_password=secrets.token_hex(32),
        )
        db_session.add(existing)
        await db_session.flush()

        await fake_redis.set("oauth:state:google-state-suffix", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-suffix-001",
                "email": "alice@google.com",  # prefix "alice" is already taken
                "name": "Alice Google",
                "picture": "",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-suffix",
                follow_redirects=False,
            )

        result = await db_session.execute(select(User).where(User.oauth_provider_id == "google-sub-suffix-001"))
        google_user = result.scalar_one_or_none()
        assert google_user is not None
        assert google_user.username == "alice1"  # first numeric suffix

    async def test_username_provider_id_fallback_when_all_suffixes_taken(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """When hint and hint1-hint9 are all taken, fall back to google_{sub} (Dev Notes)."""
        # Pre-occupy "bob" and "bob1" through "bob9"
        for i, suffix in enumerate(["", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
            db_session.add(
                User(
                    email=f"bob{suffix}@taken.example.com",
                    username=f"bob{suffix}",
                    oauth_provider="github",
                    oauth_provider_id=f"github-bob-taken-{i:03d}",
                    hashed_password=secrets.token_hex(32),
                )
            )
        await db_session.flush()

        await fake_redis.set("oauth:state:google-state-fallback", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-fallback-001",
                "email": "bob@google.com",  # prefix "bob" — all suffixes taken
                "name": "Bob Fallback",
                "picture": "",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-fallback",
                follow_redirects=False,
            )

        result = await db_session.execute(select(User).where(User.oauth_provider_id == "google-sub-fallback-001"))
        google_user = result.scalar_one_or_none()
        assert google_user is not None
        assert google_user.username == "google_google-sub-fallback-001"  # provider_id fallback

    async def test_google_token_exchange_failure_redirects_provider_denied(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
    ) -> None:
        """If Google token exchange fails (e.g. network error), redirect → provider_denied (AC-7)."""
        await fake_redis.set("oauth:state:google-state-exchfail", "google", ex=300)

        # Simulate a broken token response — no access_token field
        mock_http = AsyncMock()
        mock_http.post.return_value = MagicMock(json=MagicMock(return_value={"error": "invalid_grant"}))

        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=badcode&state=google-state-exchfail",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "provider_denied" in response.headers["location"]

    async def test_google_no_email_falls_back_to_synthetic_email(
        self,
        client: AsyncClient,
        fake_redis: FakeRedis,
        db_session: AsyncSession,
    ) -> None:
        """When Google userinfo returns no email, a synthetic placeholder is used."""
        await fake_redis.set("oauth:state:google-state-noemail2", "google", ex=300)

        mock_http = _mock_google_http(
            userinfo={
                "sub": "google-sub-noemail-002",
                "email": None,  # no email from provider
                "name": "No Email Google User",
                "picture": "https://lh3.googleusercontent.com/noemail.jpg",
            }
        )
        with patch("idp_app.api.v1.routes.auth.httpx.AsyncClient", _patch_httpx(mock_http)):
            response = await client.get(
                "/api/v1/auth/google/callback?code=authcode&state=google-state-noemail2",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)

        result = await db_session.execute(select(User).where(User.oauth_provider_id == "google-sub-noemail-002"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == "google_google-sub-noemail-002@noemail.local"
        assert user.avatar_url == "https://lh3.googleusercontent.com/noemail.jpg"
