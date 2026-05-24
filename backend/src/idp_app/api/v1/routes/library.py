"""Library endpoints."""

import json
import logging
from datetime import datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status

from idp_app.core.database import get_redis
from idp_app.schemas.library import LibraryItem, LibraryItemList

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
