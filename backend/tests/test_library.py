"""Tests for the GET /api/v1/library/items/public endpoint."""

import json
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.core.database import get_db, get_redis
from idp_app.main import create_app

# ---------------------------------------------------------------------------
# Fake Redis helpers
# ---------------------------------------------------------------------------


class FakePipeline:
    """Minimal async pipeline stub that records hgetall calls and executes them against a FakeRedis."""

    def __init__(self, store: "FakeRedis") -> None:
        self._store = store
        self._keys: list[str] = []

    def hgetall(self, key: str) -> "FakePipeline":
        self._keys.append(key)
        return self

    async def execute(self) -> list[dict[str, str]]:
        return [await self._store.hgetall(k) for k in self._keys]


class FakeRedis:
    """Minimal in-memory Redis stub supporting smembers, hgetall, and pipeline."""

    def __init__(self, data: dict[str, object] | None = None) -> None:
        self._data: dict[str, object] = data or {}

    async def smembers(self, key: str) -> set[str]:
        value = self._data.get(key, set())
        if isinstance(value, set):
            return value
        return set()

    async def hgetall(self, key: str) -> dict[str, str]:
        value = self._data.get(key, {})
        if isinstance(value, dict):
            return value
        return {}

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    async def aclose(self) -> None:
        pass


def _make_item_hash(
    *,
    title: str = "Test Skill",
    description: str = "A test skill description",
    content_type: str = "Skill",
    tags: list[str] | None = None,
    is_public: str = "true",
    target_ai: str | None = None,
    author: str | None = None,
    last_updated: str | None = None,
) -> dict[str, str]:
    h: dict[str, str] = {
        "title": title,
        "description": description,
        "content_type": content_type,
        "tags": json.dumps(tags or ["testing"]),
        "is_public": is_public,
    }
    if target_ai:
        h["target_ai"] = target_ai
    if author:
        h["author"] = author
    if last_updated:
        h["last_updated"] = last_updated
    return h


# ---------------------------------------------------------------------------
# App fixture with fake Redis and SQLite DB
# ---------------------------------------------------------------------------


@pytest.fixture
async def app_with_redis(db_session: AsyncSession) -> FastAPI:
    """App fixture that does not inject any Redis items (empty cache)."""
    fake = FakeRedis()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield fake

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    return application


@pytest.fixture
async def app_with_items(db_session: AsyncSession) -> FastAPI:
    """App fixture with two public items and one private item in the cache."""
    store: dict[str, object] = {
        "library:items:public": {"skill-one", "prompt-two"},
        "library:item:skill-one": _make_item_hash(
            title="Skill One",
            content_type="Skill",
            tags=["python", "testing"],
            is_public="true",
            author="alice",
        ),
        "library:item:prompt-two": _make_item_hash(
            title="Prompt Two",
            content_type="Prompt",
            tags=["writing"],
            is_public="true",
        ),
    }
    fake = FakeRedis(store)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield fake

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    return application


@pytest.fixture
async def app_with_private_items(db_session: AsyncSession) -> FastAPI:
    """App fixture where the public index points to a private-only item."""
    store: dict[str, object] = {
        "library:items:public": {"private-skill"},
        "library:item:private-skill": _make_item_hash(
            title="Private Skill",
            content_type="Skill",
            is_public="false",
        ),
    }
    fake = FakeRedis(store)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield fake

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    return application


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPublicLibraryEndpoint:
    """Tests for GET /api/v1/library/items/public."""

    async def test_returns_200_with_empty_cache(self, app_with_redis: FastAPI) -> None:
        """AC6: Endpoint returns HTTP 200 even when Redis is empty."""
        async with AsyncClient(transport=ASGITransport(app=app_with_redis), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        assert response.status_code == 200

    async def test_empty_cache_returns_empty_list(self, app_with_redis: FastAPI) -> None:
        """AC5: Empty library cache returns empty items list, not an error."""
        async with AsyncClient(transport=ASGITransport(app=app_with_redis), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_returns_public_items(self, app_with_items: FastAPI) -> None:
        """AC6, AC7: Endpoint returns public items with correct structure."""
        async with AsyncClient(transport=ASGITransport(app=app_with_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_no_auth_required(self, app_with_items: FastAPI) -> None:
        """AC6: No Authorization header needed."""
        async with AsyncClient(transport=ASGITransport(app=app_with_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        assert response.status_code == 200

    async def test_item_fields_present(self, app_with_items: FastAPI) -> None:
        """AC2: Each item has slug, title, description, content_type, tags, is_public."""
        async with AsyncClient(transport=ASGITransport(app=app_with_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        items = response.json()["items"]
        for item in items:
            for field in ("slug", "title", "description", "content_type", "tags", "is_public"):
                assert field in item, f"Missing field: {field}"

    async def test_no_content_field_in_items(self, app_with_items: FastAPI) -> None:
        """AC3: Full content field is NOT present in list items."""
        async with AsyncClient(transport=ASGITransport(app=app_with_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        for item in response.json()["items"]:
            assert "content" not in item

    async def test_only_public_items_returned(self, app_with_private_items: FastAPI) -> None:
        """AC7: Items where is_public=false are excluded."""
        async with AsyncClient(transport=ASGITransport(app=app_with_private_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_standard_envelope_structure(self, app_with_items: FastAPI) -> None:
        """Response follows standard envelope: items, total, page, size, pages."""
        async with AsyncClient(transport=ASGITransport(app=app_with_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        data = response.json()
        for key in ("items", "total", "page", "size", "pages"):
            assert key in data, f"Missing envelope key: {key}"

    async def test_item_content_types(self, app_with_items: FastAPI) -> None:
        """AC2: Items have content_type badges (Skill or Prompt)."""
        async with AsyncClient(transport=ASGITransport(app=app_with_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        content_types = {item["content_type"] for item in response.json()["items"]}
        assert content_types == {"Skill", "Prompt"}


class TestDecodeItemEdgeCases:
    """Tests for _decode_item edge cases (tags, missing fields, private flag)."""

    async def test_tags_as_csv_string(self, db_session: AsyncSession) -> None:
        """Comma-separated tags string is parsed correctly when JSON decode fails."""
        store: dict[str, object] = {
            "library:items:public": {"csv-skill"},
            "library:item:csv-skill": {
                "title": "CSV Skill",
                "description": "desc",
                "content_type": "Skill",
                "tags": "python,testing,ai",
                "is_public": "true",
            },
        }
        fake = FakeRedis(store)

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
            yield fake

        app = create_app()
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis] = _override_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        item = response.json()["items"][0]
        assert item["tags"] == ["python", "testing", "ai"]

    async def test_empty_hash_item_skipped(self, db_session: AsyncSession) -> None:
        """Items with an empty hash (missing title) are silently skipped."""
        store: dict[str, object] = {
            "library:items:public": {"ghost-slug"},
            "library:item:ghost-slug": {},  # empty hash
        }
        fake = FakeRedis(store)

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
            yield fake

        app = create_app()
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis] = _override_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_redis_smembers_error_returns_empty_list(self, db_session: AsyncSession) -> None:
        """AC5: Redis error on smembers results in a graceful empty response."""

        class BrokenRedis(FakeRedis):
            async def smembers(self, key: str) -> set[str]:
                raise ConnectionError("Redis unavailable")

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        async def _override_get_redis() -> AsyncGenerator[BrokenRedis, None]:
            yield BrokenRedis()

        app = create_app()
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis] = _override_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_redis_hgetall_error_skips_item(self, db_session: AsyncSession) -> None:
        """AC5: Redis error on hgetall for a specific item skips that item gracefully."""

        class PartiallyBrokenRedis(FakeRedis):
            async def hgetall(self, key: str) -> dict[str, str]:
                raise ConnectionError("Redis unavailable")

        store: dict[str, object] = {"library:items:public": {"broken-item"}}
        fake = PartiallyBrokenRedis(store)

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        async def _override_get_redis() -> AsyncGenerator[PartiallyBrokenRedis, None]:
            yield fake

        app = create_app()
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis] = _override_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items/public")
        assert response.status_code == 200
        assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# Fixtures for GET /api/v1/library/items (authenticated)
# ---------------------------------------------------------------------------

_ALL_ITEMS_STORE: dict[str, object] = {
    "library:items": {"skill-python", "prompt-writing", "skill-devops"},
    "library:item:skill-python": _make_item_hash(
        title="Python Skill",
        content_type="Skill",
        tags=["python", "testing"],
        is_public="true",
        target_ai="claude",
        author="alice",
    ),
    "library:item:prompt-writing": _make_item_hash(
        title="Writing Prompt",
        content_type="Prompt",
        tags=["writing", "creativity"],
        is_public="true",
        target_ai="chatgpt",
        author="bob",
    ),
    "library:item:skill-devops": _make_item_hash(
        title="DevOps Skill",
        content_type="Skill",
        tags=["devops", "docker"],
        is_public="false",
        target_ai="claude",
    ),
}


def _make_app_with_all_items(db_session: AsyncSession) -> FastAPI:
    """Helper: create app with library:items store."""
    fake = FakeRedis(_ALL_ITEMS_STORE)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield fake

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    return application


@pytest.fixture
async def app_authed_items(db_session: AsyncSession) -> FastAPI:
    """App fixture with three library items (two Skills, one Prompt)."""
    return _make_app_with_all_items(db_session)


async def _get_token(ac: AsyncClient) -> str:
    """Register a user and return a bearer token."""
    await ac.post(
        "/api/v1/users",
        json={"email": "libtest@example.com", "username": "libtest", "password": "P@ssw0rd123"},
    )
    resp = await ac.post(
        "/api/v1/auth/token",
        data={"username": "libtest", "password": "P@ssw0rd123"},
    )
    return str(resp.json()["access_token"])


# ---------------------------------------------------------------------------
# Tests for GET /api/v1/library/items (AC: 10, 11, 12)
# ---------------------------------------------------------------------------


class TestAuthenticatedLibraryListEndpoint:
    """Tests for GET /api/v1/library/items — authenticated, server-side filtering."""

    async def test_401_without_jwt(self, app_authed_items: FastAPI) -> None:
        """AC 11: No JWT → HTTP 401."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            response = await ac.get("/api/v1/library/items")
        assert response.status_code == 401

    async def test_200_with_jwt(self, app_authed_items: FastAPI) -> None:
        """AC 10: Valid JWT → HTTP 200."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    async def test_standard_envelope_returned(self, app_authed_items: FastAPI) -> None:
        """AC 10: Response contains standard envelope fields."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        for key in ("items", "total", "page", "size", "pages"):
            assert key in data, f"Missing envelope key: {key}"

    async def test_returns_all_items_unfiltered(self, app_authed_items: FastAPI) -> None:
        """AC 10: All 3 items returned when no filters applied."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["total"] == 3

    async def test_filter_by_content_type(self, app_authed_items: FastAPI) -> None:
        """AC 6: ?type=Skill returns only Skills."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items?type=Skill", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["total"] == 2
        assert all(i["content_type"] == "Skill" for i in data["items"])

    async def test_filter_by_target_ai(self, app_authed_items: FastAPI) -> None:
        """AC 7: ?target_ai=claude returns only claude items."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get(
                "/api/v1/library/items?target_ai=claude", headers={"Authorization": f"Bearer {token}"}
            )
        data = response.json()
        assert data["total"] == 2
        assert all(i["target_ai"] == "claude" for i in data["items"])

    async def test_filter_by_tags(self, app_authed_items: FastAPI) -> None:
        """AC 8: ?tags=python returns items containing that tag."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items?tags=python", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Python Skill"

    async def test_search_by_q(self, app_authed_items: FastAPI) -> None:
        """AC 4: ?q=writing returns items matching the search term."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items?q=writing", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Writing Prompt"

    async def test_combined_filters_and_logic(self, app_authed_items: FastAPI) -> None:
        """AC 9: Combining type=Skill and target_ai=claude applies AND logic."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get(
                "/api/v1/library/items?type=Skill&target_ai=claude",
                headers={"Authorization": f"Bearer {token}"},
            )
        data = response.json()
        assert data["total"] == 2
        titles = {i["title"] for i in data["items"]}
        assert titles == {"Python Skill", "DevOps Skill"}

    async def test_no_results_returns_empty_list(self, app_authed_items: FastAPI) -> None:
        """AC 5: No matching results → empty items list, not an error."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get(
                "/api/v1/library/items?q=nonexistent_zxq99",
                headers={"Authorization": f"Bearer {token}"},
            )
        data = response.json()
        assert response.status_code == 200
        assert data["total"] == 0
        assert data["items"] == []

    async def test_pagination_page_and_size(self, app_authed_items: FastAPI) -> None:
        """AC 10: Pagination params page and size work correctly."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items?page=1&size=2", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert data["total"] == 3
        assert data["pages"] == 2
        assert data["size"] == 2
        assert len(data["items"]) == 2

    async def test_pagination_second_page(self, app_authed_items: FastAPI) -> None:
        """AC 10: Second page returns remaining items."""
        async with AsyncClient(transport=ASGITransport(app=app_authed_items), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items?page=2&size=2", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert len(data["items"]) == 1

    async def test_empty_redis_returns_empty_list(self, db_session: AsyncSession) -> None:
        """AC 12: Empty library:items key → empty list, no error."""
        fake = FakeRedis({})

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
            yield fake

        app = create_app()
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis] = _override_get_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            token = await _get_token(ac)
            response = await ac.get("/api/v1/library/items", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["items"] == []
