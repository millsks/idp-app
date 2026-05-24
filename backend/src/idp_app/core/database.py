"""SQLAlchemy async engine, session factory, and base model.

The engine and session factory are created lazily on first use so that
importing this module does not load asyncpg (which lets the test suite
swap in an aiosqlite engine via dependency_overrides without side-effects).
"""

import functools
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from idp_app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


@functools.lru_cache(maxsize=1)
def _get_engine() -> AsyncEngine:
    """Build and cache the production async engine (postgresql+asyncpg)."""
    settings = get_settings()
    # Normalise both plain postgres:// and postgresql:// schemes
    raw_url = str(settings.DATABASE_URL)
    db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(
        db_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


@functools.lru_cache(maxsize=1)
def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Build and cache the session factory bound to the production engine."""
    return async_sessionmaker(
        _get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a transactional database session."""
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
