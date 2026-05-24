"""Shared pytest fixtures for the backend test suite."""

import os
from collections.abc import AsyncGenerator

# Provide a dummy DB_PASSWORD so Settings can be instantiated in tests.
# The actual database connection is overridden with an in-memory SQLite engine.
os.environ.setdefault("DB_PASSWORD", "test-password-not-used")

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from idp_app.core.database import Base, get_db, get_redis
from idp_app.main import create_app

# In-memory SQLite via aiosqlite.
# StaticPool keeps a single connection so the schema persists across
# all requests made within a single test.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fake Redis — simple async in-memory replacement for tests
# ---------------------------------------------------------------------------


class FakeRedis:
    """Minimal async Redis stand-in for unit/integration tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite engine for one test, in the same event loop."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Transactional session that rolls back after each test."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Fresh FakeRedis instance per test."""
    return FakeRedis()


@pytest.fixture
async def app(db_session: AsyncSession, fake_redis: FakeRedis) -> FastAPI:
    """FastAPI application with the test database and fake Redis injected."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
        yield fake_redis

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client backed by the in-process ASGI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
