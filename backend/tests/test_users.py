"""Tests for the /api/v1/users endpoints."""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.core.security import create_access_token
from idp_app.models.user import User


@pytest.fixture
async def created_user(client: AsyncClient) -> dict[str, object]:
    """Create a user and return the response body."""
    payload = {
        "email": "alice@example.com",
        "username": "alice",
        "full_name": "Alice Example",
        "password": "supersecret1",
    }
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


class TestCreateUser:
    async def test_create_user_success(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "bob@example.com",
                "username": "bob",
                "password": "supersecret2",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "bob"
        assert data["email"] == "bob@example.com"
        assert "id" in data
        # Password must never be returned
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_create_duplicate_user_returns_409(
        self, client: AsyncClient, created_user: dict[str, object]
    ) -> None:
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "alice@example.com",
                "username": "alice",
                "password": "supersecret1",
            },
        )
        assert response.status_code == 409


class TestGetUser:
    async def test_get_existing_user(self, client: AsyncClient, created_user: dict[str, object]) -> None:
        user_id = created_user["id"]
        response = await client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

    async def test_get_nonexistent_user_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users/99999")
        assert response.status_code == 404


class TestUpdateUser:
    async def test_update_user_success(self, client: AsyncClient, created_user: dict[str, object]) -> None:
        user_id = created_user["id"]
        response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Alice Updated"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Alice Updated"

    async def test_update_nonexistent_user_returns_404(self, client: AsyncClient) -> None:
        response = await client.patch("/api/v1/users/99999", json={"full_name": "Ghost"})
        assert response.status_code == 404


@pytest.fixture
async def oauth_user(db_session: AsyncSession) -> User:
    """Create an OAuth-backed user for /users/me endpoint tests."""
    user = User(
        email="me@example.com",
        username="me-user",
        full_name="Me User",
        hashed_password="oauth-only",
        oauth_provider="github",
        oauth_provider_id="gh_12345",
        avatar_url="https://avatars.example.com/me.png",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(oauth_user: User) -> dict[str, str]:
    """Return bearer auth headers for the oauth_user fixture."""
    token = create_access_token(data={"sub": oauth_user.username})
    return {"Authorization": f"Bearer {token}"}


class TestCurrentUserEndpoints:
    async def test_get_me_returns_profile_payload(
        self,
        client: AsyncClient,
        oauth_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == oauth_user.id
        assert data["email"] == "me@example.com"
        assert data["full_name"] == "Me User"
        assert data["avatar_url"] == "https://avatars.example.com/me.png"
        assert data["oauth_provider"] == "github"
        assert data["is_active"] is True
        assert data["is_superuser"] is True
        assert data["created_at"]

    async def test_get_me_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_with_expired_token_returns_401(self, client: AsyncClient, oauth_user: User) -> None:
        expired_token = create_access_token(data={"sub": oauth_user.username}, expires_delta=timedelta(minutes=-1))
        response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401

    async def test_patch_me_updates_full_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = await client.patch("/api/v1/users/me", headers=auth_headers, json={"full_name": "Updated Me"})
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Me"

    async def test_patch_me_blank_name_returns_422(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = await client.patch("/api/v1/users/me", headers=auth_headers, json={"full_name": "   "})
        assert response.status_code == 422

    async def test_patch_me_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.patch("/api/v1/users/me", json={"full_name": "Nope"})
        assert response.status_code == 401

    async def test_patch_me_cannot_modify_is_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"full_name": "Still Super", "is_superuser": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Still Super"
        assert data["is_superuser"] is True
