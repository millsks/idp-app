"""Tests for the /api/v1/users endpoints."""

import pytest
from httpx import AsyncClient


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
        response = await client.get("/api/v1/users/999999")
        assert response.status_code == 404


class TestUpdateUser:
    async def test_update_full_name(self, client: AsyncClient, created_user: dict[str, object]) -> None:
        user_id = created_user["id"]
        response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Alice Updated"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Alice Updated"

    async def test_update_nonexistent_user_returns_404(self, client: AsyncClient) -> None:
        response = await client.patch("/api/v1/users/999999", json={"full_name": "Ghost"})
        assert response.status_code == 404
