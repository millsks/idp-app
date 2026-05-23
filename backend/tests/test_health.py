"""Tests for the health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """GET /api/v1/health should return 200 with status=ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_version_format(client: AsyncClient) -> None:
    """Health response version should be a semver string."""
    response = await client.get("/api/v1/health")
    version = response.json()["version"]
    parts = version.split(".")
    assert len(parts) == 3  # noqa: PLR2004
    assert all(part.isdigit() for part in parts)
