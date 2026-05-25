"""Library endpoints."""

import json
import logging
import math
from datetime import datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from idp_app.core.config import Settings, get_settings
from idp_app.core.database import get_redis
from idp_app.core.security import get_current_user
from idp_app.models.user import User
from idp_app.schemas.library import LibraryItem, LibraryItemDetail, LibraryItemList, LibrarySyncStatus

logger = logging.getLogger(__name__)

router = APIRouter()

_PUBLIC_INDEX_KEY = "library:items:public"
_ALL_ITEMS_KEY = "library:items"
_ITEM_KEY_PREFIX = "library:item:"
_CACHE_UNAVAILABLE_MSG = "Library cache is temporarily unavailable."


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


@router.get(
    "/items",
    response_model=LibraryItemList,
    status_code=status.HTTP_200_OK,
    summary="List library items (authenticated)",
)
async def list_library_items(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
    content_type: Annotated[
        str | None, Query(alias="type", description="Filter by content_type (Skill or Prompt)")
    ] = None,
    tags: Annotated[list[str] | None, Query(description="Filter by tag(s) — AND logic")] = None,
    target_ai: Annotated[str | None, Query(description="Filter by target AI assistant")] = None,
    q: Annotated[str | None, Query(description="Full-text search across title, description, tags, content")] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> LibraryItemList:
    """Return paginated, filtered library items from the Redis cache.

    Requires a valid JWT.  Filtering and search are performed in-memory after
    fetching all items from Redis using a pipeline for efficiency.
    Returns HTTP 503 when Redis is unavailable; empty list when the cache is
    genuinely empty.
    """
    try:
        slugs: set[str] = await redis.smembers(_ALL_ITEMS_KEY)
    except Exception as exc:
        logger.exception("Redis error reading %s", _ALL_ITEMS_KEY)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_CACHE_UNAVAILABLE_MSG,
        ) from exc

    all_items: list[LibraryItem] = []
    slug_to_content: dict[str, str] = {}  # kept for full-text search (AC 4)

    if slugs:
        slug_list = list(slugs)
        try:
            pipe = redis.pipeline()
            for slug in slug_list:
                pipe.hgetall(f"{_ITEM_KEY_PREFIX}{slug}")
            raw_results: list[dict[str, str]] = await pipe.execute()
        except Exception as exc:
            logger.exception("Redis pipeline error fetching library items")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_CACHE_UNAVAILABLE_MSG,
            ) from exc

        for slug, raw in zip(slug_list, raw_results, strict=False):
            if not raw:
                logger.warning("Orphaned slug in %s: %s — hash missing, skipping", _ALL_ITEMS_KEY, slug)
                continue
            item = _decode_item(slug, raw)
            if item is None:
                continue
            slug_to_content[slug] = raw.get("content", "")
            all_items.append(item)

    # In-memory filtering (AC: 6-9, 12)
    filtered: list[LibraryItem] = []
    for item in all_items:
        if content_type is not None and item.content_type != content_type:
            continue
        if target_ai is not None and item.target_ai != target_ai:
            continue
        if tags:
            item_tags_lower = {t.lower() for t in (item.tags or [])}
            if not all(t.lower() in item_tags_lower for t in tags):
                continue
        if q:
            q_lower = q.lower()
            content_text = slug_to_content.get(item.slug, "")
            searchable = " ".join(filter(None, [item.title, item.description, " ".join(item.tags or []), content_text]))
            if q_lower not in searchable.lower():
                continue
        filtered.append(item)

    total = len(filtered)
    pages = math.ceil(total / size) if total > 0 else 0
    start = (page - 1) * size
    paginated = filtered[start : start + size]

    return LibraryItemList(
        items=paginated,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


def _compute_github_url(
    slug: str,
    content_type: str,
    owner: str,
    repo: str,
    branch: str,
) -> str | None:
    """Compute the GitHub blob URL for a library item's source file.

    Skills live at ``skills/{slug}/SKILL.md``; prompts at ``prompts/{slug}.md``.
    Returns ``None`` when owner, repo, or branch are not configured, or when
    ``content_type`` is an unrecognised value.
    """
    if not owner or not repo or not branch:
        return None
    if content_type == "Skill":
        path = f"skills/{slug}/SKILL.md"
    elif content_type == "Prompt":
        path = f"prompts/{slug}.md"
    else:
        logger.warning("Unknown content_type %r for slug %r — cannot compute GitHub URL", content_type, slug)
        return None
    return f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"


@router.get(
    "/items/{slug}",
    response_model=LibraryItemDetail,
    status_code=status.HTTP_200_OK,
    summary="Get a single library item by slug (authenticated)",
)
async def get_library_item(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9-]{0,98}[a-z0-9]$|^[a-z0-9]$")],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
    settings: Annotated[Settings, Depends(get_settings)],
) -> LibraryItemDetail:
    """Return full detail for a single library item, including its raw Markdown content.

    Requires a valid JWT — HTTP 401 is returned by the ``get_current_user`` dependency
    when the token is missing or invalid.  Returns HTTP 404 when the slug does not exist
    in the Redis cache.  Returns HTTP 503 when Redis is unreachable.
    """
    try:
        raw: dict[str, str] = await redis.hgetall(f"{_ITEM_KEY_PREFIX}{slug}")
    except Exception as exc:
        logger.exception("Redis error reading item %s", slug)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_CACHE_UNAVAILABLE_MSG,
        ) from exc

    item = _decode_item(slug, raw)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Library item '{slug}' not found.",
        )

    content = raw.get("content", "")
    github_url = _compute_github_url(
        slug=slug,
        content_type=item.content_type,
        owner=settings.GITHUB_CONTENT_OWNER,
        repo=settings.GITHUB_CONTENT_REPO,
        branch=settings.GITHUB_CONTENT_BRANCH,
    )

    return LibraryItemDetail(
        **item.model_dump(),
        content=content,
        github_url=github_url,
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
