"""Library endpoints."""

import json
import logging
from datetime import datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status

from idp_app.core.database import get_redis
from idp_app.core.security import get_current_user
from idp_app.models.user import User
from idp_app.schemas.library import LibraryItem, LibraryItemList, LibrarySyncStatus

logger = logging.getLogger(__name__)

router = APIRouter()

_PUBLIC_INDEX_KEY = "library:items:public"
_ITEM_KEY_PREFIX = "library:item:"


def _decode_item(slug: str, raw: dict[str, str]) -> LibraryItem | None:
    """Convert a Redis Hash (all string values) to a LibraryItem.

    Returns *None* if the hash is empty or missing required fields.
    """
    if not raw or "title" not in raw:
        return None

    tags_raw = raw.get("tags", "[]")
    try:
        tags: list[str] = json.loads(tags_raw)
    except (json.JSONDecodeError, ValueError):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    last_updated_raw = raw.get("last_updated")
    last_updated = None
    if last_updated_raw:
        try:
            last_updated = datetime.fromisoformat(last_updated_raw)
        except ValueError:
            pass

    return LibraryItem(
        slug=slug,
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        content_type=raw.get("content_type", ""),
        tags=tags,
        is_public=raw.get("is_public", "false").lower() in {"1", "true", "yes"},
        target_ai=raw.get("target_ai") or None,
        author=raw.get("author") or None,
        last_updated=last_updated,
    )


@router.get(
    "/items/public",
    response_model=LibraryItemList,
    status_code=status.HTTP_200_OK,
    summary="List public library items",
)
async def list_public_library_items(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
) -> LibraryItemList:
    """Return up to all public library items from the Redis cache.

    This endpoint is fully public — no authentication required.
    Returns an empty list when the cache key does not exist.
    Only items where ``is_public=true`` in the cache hash are included.
    """
    try:
        slugs: set[str] = await redis.smembers(_PUBLIC_INDEX_KEY)
    except Exception:
        logger.exception("Redis error reading %s", _PUBLIC_INDEX_KEY)
        slugs = set()

    items: list[LibraryItem] = []
    for slug in slugs:
        try:
            raw: dict[str, str] = await redis.hgetall(f"{_ITEM_KEY_PREFIX}{slug}")
        except Exception:
            logger.exception("Redis error reading item %s", slug)
            continue

        item = _decode_item(slug, raw)
        if item is not None and item.is_public:
            items.append(item)

    total = len(items)
    return LibraryItemList(
        items=items,
        total=total,
        page=1,
        size=total,
        pages=1 if total > 0 else 0,
    )


@router.post(
    "/refresh",
    response_model=LibrarySyncStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an immediate library sync",
)
async def trigger_library_refresh(
    current_user: Annotated[User, Depends(get_current_user)],
) -> LibrarySyncStatus:
    """Enqueue an immediate ``library.sync_content`` Celery task.

    Any authenticated user may trigger this endpoint.  The task runs
    asynchronously in the background — this endpoint returns HTTP 202
    immediately with the Celery task ID.

    Returns HTTP 503 when the Celery broker is unavailable.
    """
    try:
        # Import here to avoid worker.py circular import at module load time
        from idp_app.tasks.library_sync import sync_library_content

        result = sync_library_content.delay()
        return LibrarySyncStatus(
            task_id=result.id,
            status="accepted",
            message="Library sync task enqueued successfully.",
        )
    except Exception as exc:
        logger.exception("Failed to enqueue library sync task: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to enqueue sync task — Celery broker may be unavailable.",
        ) from exc
