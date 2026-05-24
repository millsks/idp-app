"""Tests for the /api/v1/auth endpoints."""

import secrets
from unittest.mock import AsyncMock, MagicMock, patch

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
