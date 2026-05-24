"""Tests for the /api/v1/auth endpoints."""

import pytest
from httpx import AsyncClient


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
