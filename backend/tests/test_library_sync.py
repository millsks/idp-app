"""Tests for:
- idp_app.services.github_content  (unit tests with mocked httpx responses)
- idp_app.tasks.library_sync       (task integration tests with fake Redis)
- POST /api/v1/library/refresh     (endpoint tests)
"""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncGenerator
from collections.abc import Set as AbstractSet
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from idp_app.core.database import get_db, get_redis
from idp_app.main import create_app
from idp_app.services.github_content import (
    derive_content_type,
    derive_slug,
    get_file_content,
    get_file_tree,
    get_last_commit,
    parse_frontmatter,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_MD = """\
---
title: My Skill
description: A helpful skill.
tags:
  - python
  - testing
is_public: true
---

# My Skill

Full content here.
"""

_PROMPT_MD = """\
---
title: My Prompt
description: A useful prompt.
tags:
  - writing
is_public: false
---

Prompt body.
"""


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


# ---------------------------------------------------------------------------
# Fake Redis for pipeline tests
# ---------------------------------------------------------------------------


class FakeRedisPipeline:
    """Minimal pipeline that records commands and executes them against a store."""

    def __init__(self, store: dict[str, Any]) -> None:
        self._store = store
        self._cmds: list[Any] = []

    def delete(self, *keys: str) -> FakeRedisPipeline:
        for k in keys:
            self._cmds.append(("del", k))
        return self

    def hset(self, name: str, mapping: dict[str, str]) -> FakeRedisPipeline:
        self._cmds.append(("hset", name, mapping))
        return self

    def sadd(self, key: str, *members: str) -> FakeRedisPipeline:
        self._cmds.append(("sadd", key, members))
        return self

    def set(self, key: str, value: str) -> FakeRedisPipeline:
        self._cmds.append(("set", key, value))
        return self

    def execute(self) -> list[Any]:
        for cmd in self._cmds:
            if cmd[0] == "del":
                self._store.pop(cmd[1], None)
            elif cmd[0] == "hset":
                self._store[cmd[1]] = cmd[2]
            elif cmd[0] == "sadd":
                existing = self._store.setdefault(cmd[1], set())
                existing.update(cmd[2])
            elif cmd[0] == "set":
                self._store[cmd[1]] = cmd[2]
        return []


class FakeSyncRedis:
    """Synchronous fake Redis for use inside the Celery task (which uses sync Redis)."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    def get(self, key: str) -> str | None:
        v = self._store.get(key)
        return v if isinstance(v, str) else None

    def smembers(self, key: str) -> AbstractSet[str]:
        v = self._store.get(key, set())
        return v if isinstance(v, set) else set()

    def hgetall(self, key: str) -> dict[str, str]:
        v = self._store.get(key, {})
        return v if isinstance(v, dict) else {}

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self._store)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    @classmethod
    def from_url(cls, *_args: Any, **_kwargs: Any) -> FakeSyncRedis:
        return cls()


# ---------------------------------------------------------------------------
# ── Unit tests: services.github_content ─────────────────────────────────────
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_parses_valid_yaml(self) -> None:
        result = parse_frontmatter(_SKILL_MD)
        assert result["title"] == "My Skill"
        assert result["tags"] == ["python", "testing"]
        assert result["is_public"] is True

    def test_returns_empty_when_no_frontmatter(self) -> None:
        assert parse_frontmatter("# Just markdown") == {}

    def test_returns_empty_on_malformed_yaml(self) -> None:
        bad = "---\n: invalid: [{unclosed\n---\n"
        assert parse_frontmatter(bad) == {}

    def test_returns_empty_when_closing_delimiter_missing(self) -> None:
        assert parse_frontmatter("---\ntitle: No close") == {}

    def test_strips_leading_whitespace(self) -> None:
        result = parse_frontmatter("  \n" + _SKILL_MD)
        # strip() normalises leading whitespace
        assert result["title"] == "My Skill"


class TestDeriveHelpers:
    def test_derive_slug_skill(self) -> None:
        assert derive_slug("skills/my-skill/SKILL.md") == "my-skill"

    def test_derive_slug_prompt(self) -> None:
        assert derive_slug("prompts/my-prompt.md") == "my-prompt"

    def test_derive_content_type_skill(self) -> None:
        assert derive_content_type("skills/x/SKILL.md") == "Skill"

    def test_derive_content_type_prompt(self) -> None:
        assert derive_content_type("prompts/x.md") == "Prompt"


@pytest.mark.asyncio
class TestGetFileTree:
    async def test_returns_matching_paths(self) -> None:
        tree_response = {
            "tree": [
                {"type": "blob", "path": "skills/cool-skill/SKILL.md"},
                {"type": "blob", "path": "prompts/nice-prompt.md"},
                {"type": "blob", "path": "README.md"},
                {"type": "tree", "path": "skills/cool-skill"},  # directory node
            ]
        }
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = tree_response
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        paths = await get_file_tree(mock_client, "owner", "repo", "main", token="tok")
        assert "skills/cool-skill/SKILL.md" in paths
        assert "prompts/nice-prompt.md" in paths
        assert "README.md" not in paths

    async def test_rate_limit_warning_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = {"tree": []}
        mock_response.headers = {"X-RateLimit-Remaining": "10", "X-RateLimit-Limit": "50"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        import logging

        with caplog.at_level(logging.WARNING, logger="idp_app.services.github_content"):
            await get_file_tree(mock_client, "owner", "repo", "main", token="tok")

        assert any("rate limit" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
class TestGetFileContent:
    async def test_decodes_base64_content(self) -> None:
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = {"content": _b64(_SKILL_MD)}
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        content = await get_file_content(mock_client, "owner", "repo", "skills/x/SKILL.md", token="tok")
        assert "My Skill" in content

    async def test_handles_multiline_base64(self) -> None:
        """GitHub wraps base64 content at 60 chars per line."""
        raw = base64.b64encode(_SKILL_MD.encode()).decode()
        chunked = "\n".join(raw[i : i + 60] for i in range(0, len(raw), 60)) + "\n"

        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = {"content": chunked}
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        content = await get_file_content(mock_client, "owner", "repo", "skills/x/SKILL.md", token="tok")
        assert content == _SKILL_MD


@pytest.mark.asyncio
class TestGetLastCommit:
    async def test_returns_author_and_date(self) -> None:
        payload = [
            {
                "committer": {"login": "alice"},
                "commit": {"committer": {"date": "2026-05-01T12:00:00Z"}},
            }
        ]
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = payload
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        result = await get_last_commit(mock_client, "owner", "repo", "skills/x/SKILL.md", token="tok")
        assert result["author"] == "alice"
        assert result["last_updated"] == "2026-05-01T12:00:00Z"

    async def test_returns_nones_when_no_commits(self) -> None:
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = []
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        result = await get_last_commit(mock_client, "owner", "repo", "skills/x/SKILL.md", token="tok")
        assert result["author"] is None
        assert result["last_updated"] is None


# ---------------------------------------------------------------------------
# ── Integration tests: library.sync_content Celery task ─────────────────────
# ---------------------------------------------------------------------------


class TestSyncLibraryContentTask:
    """Tests for the sync_library_content Celery task.

    The task runs async GitHub API calls via asyncio.run().  We mock the
    async _fetch_and_build_items helper and patch the sync Redis client so no
    real broker or Redis is needed.
    """

    def _run_task(
        self,
        items: list[dict[str, Any]],
        fake_store: FakeSyncRedis,
    ) -> dict[str, Any]:
        """Invoke the task synchronously via .apply().get()."""
        from idp_app.tasks.library_sync import sync_library_content

        with (
            patch("idp_app.tasks.library_sync._fetch_and_build_items", new_callable=AsyncMock) as mock_fetch,
            patch("idp_app.tasks.library_sync.sync_redis") as mock_sync_redis_module,
        ):
            mock_fetch.return_value = items
            mock_sync_redis_module.from_url.return_value = fake_store
            return sync_library_content.apply().get()  # type: ignore[no-any-return]

    def test_writes_items_to_redis(self) -> None:
        store = FakeSyncRedis()
        items = [
            {
                "slug": "my-skill",
                "title": "My Skill",
                "description": "desc",
                "content_type": "Skill",
                "tags": json.dumps(["python"]),
                "is_public": "true",
                "target_ai": "",
                "author": "alice",
                "last_updated": "2026-05-01T00:00:00Z",
            }
        ]
        result = self._run_task(items, store)

        assert result["status"] == "ok"
        assert result["items_synced"] == 1
        assert "my-skill" in store.smembers("library:items")
        assert "my-skill" in store.smembers("library:items:public")
        assert store.hgetall("library:item:my-skill")["title"] == "My Skill"

    def test_private_items_not_in_public_index(self) -> None:
        store = FakeSyncRedis()
        items = [
            {
                "slug": "private-prompt",
                "title": "Private",
                "description": "",
                "content_type": "Prompt",
                "tags": "[]",
                "is_public": "false",
                "target_ai": "",
                "author": "",
                "last_updated": "",
            }
        ]
        result = self._run_task(items, store)

        assert result["status"] == "ok"
        assert "private-prompt" in store.smembers("library:items")
        assert "private-prompt" not in store.smembers("library:items:public")

    def test_sets_sync_status_ok(self) -> None:
        store = FakeSyncRedis()
        result = self._run_task([], store)
        assert result["status"] == "ok"
        assert store.get("library:sync_status") == "ok"

    def test_sets_last_refresh_timestamp(self) -> None:
        store = FakeSyncRedis()
        self._run_task([], store)
        ts = store.get("library:last_refresh")
        assert ts is not None
        assert int(ts) > 0

    def test_zero_items_writes_empty_indexes(self) -> None:
        store = FakeSyncRedis()
        result = self._run_task([], store)
        assert result["items_synced"] == 0
        assert store.smembers("library:items") == set()

    def test_sets_status_error_on_failure(self) -> None:
        """On uncaught exception the task sets sync_status to error:… and retries."""
        from idp_app.tasks.library_sync import sync_library_content

        fake_store = FakeSyncRedis()

        with (
            patch("idp_app.tasks.library_sync._fetch_and_build_items", new_callable=AsyncMock) as mock_fetch,
            patch("idp_app.tasks.library_sync.sync_redis") as mock_redis_module,
        ):
            mock_fetch.side_effect = RuntimeError("network error")
            mock_redis_module.from_url.return_value = fake_store

            # In ALWAYS_EAGER mode apply() captures retries; task will be FAILURE
            result = sync_library_content.apply()
            assert result.failed()

        status = fake_store.get("library:sync_status")
        assert status is not None
        assert status.startswith("error:")

    def test_multiple_items_all_indexed(self) -> None:
        store = FakeSyncRedis()
        items = [
            {
                "slug": "skill-a",
                "title": "Skill A",
                "description": "",
                "content_type": "Skill",
                "tags": "[]",
                "is_public": "true",
                "target_ai": "",
                "author": "",
                "last_updated": "",
            },
            {
                "slug": "prompt-b",
                "title": "Prompt B",
                "description": "",
                "content_type": "Prompt",
                "tags": "[]",
                "is_public": "false",
                "target_ai": "",
                "author": "",
                "last_updated": "",
            },
        ]
        result = self._run_task(items, store)
        assert result["items_synced"] == 2
        assert store.smembers("library:items") == {"skill-a", "prompt-b"}
        assert store.smembers("library:items:public") == {"skill-a"}


# ---------------------------------------------------------------------------
# ── Endpoint tests: POST /api/v1/library/refresh ─────────────────────────────
# ---------------------------------------------------------------------------


class FakeAsyncRedis:
    """Minimal async Redis stub for endpoint tests."""

    async def smembers(self, _key: str) -> set[str]:
        return set()

    async def hgetall(self, _key: str) -> dict[str, str]:
        return {}

    async def aclose(self) -> None:
        pass


@pytest.fixture
async def library_refresh_app(db_session: AsyncSession) -> FastAPI:
    from idp_app.core.security import get_current_user
    from idp_app.models.user import User

    _fake_user = User(
        id=1,
        email="testuser@example.com",
        username="testuser",
        hashed_password="hashed",
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeAsyncRedis, None]:
        yield FakeAsyncRedis()

    async def _override_get_current_user() -> User:
        return _fake_user

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    application.dependency_overrides[get_current_user] = _override_get_current_user
    return application


@pytest.fixture
async def auth_client(library_refresh_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Client that always presents as authenticated (get_current_user is overridden)."""
    async with AsyncClient(
        transport=ASGITransport(app=library_refresh_app),
        base_url="http://test",
        headers={"Authorization": "Bearer faketoken"},
    ) as ac:
        yield ac


@pytest.fixture
async def anon_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated client — uses real auth stack so 401s work correctly."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeAsyncRedis, None]:
        yield FakeAsyncRedis()

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as ac:
        yield ac


class TestLibraryRefreshEndpoint:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, anon_client: AsyncClient) -> None:
        response = await anon_client.post("/api/v1/library/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticated_returns_202_and_task_id(self, auth_client: AsyncClient) -> None:
        mock_result = MagicMock()
        mock_result.id = "test-task-uuid-1234"

        # Patch the task at its source module so the local import in the endpoint
        # picks up the mock.
        with patch(
            "idp_app.tasks.library_sync.sync_library_content",
            autospec=True,
        ) as mock_task:
            mock_task.delay.return_value = mock_result
            response = await auth_client.post("/api/v1/library/refresh")

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["task_id"] == "test-task-uuid-1234"
        mock_task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_unavailable_returns_503(self, auth_client: AsyncClient) -> None:
        with patch(
            "idp_app.tasks.library_sync.sync_library_content",
            autospec=True,
        ) as mock_task:
            mock_task.delay.side_effect = Exception("broker connection refused")
            response = await auth_client.post("/api/v1/library/refresh")

        assert response.status_code == 503

        assert response.status_code == 503
