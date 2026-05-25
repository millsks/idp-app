"""Celery task: sync AI skills and prompts from GitHub into Redis.

The task is named ``library.sync_content`` and is scheduled via Celery Beat
to run on application startup and every ``LIBRARY_CACHE_TTL`` seconds.

Redis key schema
----------------
- ``library:items``        — Set of all synced slugs
- ``library:items:public`` — Set of slugs where ``is_public=true``
- ``library:item:{slug}``  — Hash with item fields (all values are strings)
- ``library:last_refresh``  — Unix timestamp of last successful sync
- ``library:sync_status``   — ``"ok"``, ``"running"``, or ``"error:{message}"``

Design notes
------------
- Celery workers run synchronously by default; ``asyncio.run()`` is used to
  drive the async GitHub API calls from inside the synchronous Celery task.
- The Redis pipeline is executed atomically: old index keys are deleted and
  all new items are written in a single ``pipeline.execute()`` call so readers
  never see a partially-synced state.
- On error the existing cached items are preserved (stale cache strategy).
- List-type fields (``tags``, ``target_ai``) are stored as JSON strings.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
import redis as sync_redis

from idp_app.core.config import get_settings
from idp_app.services.github_content import (
    derive_content_type,
    derive_slug,
    get_file_content,
    get_file_tree,
    get_last_commit,
    parse_frontmatter,
)
from idp_app.tasks.worker import app as celery_app

logger = logging.getLogger(__name__)

_ITEMS_KEY = "library:items"
_PUBLIC_KEY = "library:items:public"
_ITEM_PREFIX = "library:item:"
_LAST_REFRESH_KEY = "library:last_refresh"
_SYNC_STATUS_KEY = "library:sync_status"


# ---------------------------------------------------------------------------
# Async sync implementation
# ---------------------------------------------------------------------------


async def _fetch_and_build_items(settings: Any) -> list[dict[str, Any]]:
    """Fetch all skills and prompts from GitHub and return a list of item dicts."""
    token = settings.GITHUB_CONTENT_TOKEN
    owner = settings.GITHUB_CONTENT_OWNER
    repo = settings.GITHUB_CONTENT_REPO
    branch = settings.GITHUB_CONTENT_BRANCH

    items: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        paths = await get_file_tree(client, owner, repo, branch, token=token)
        logger.info("library.sync_content: found %d content paths", len(paths))

        for path in paths:
            try:
                slug = derive_slug(path)
                content_type = derive_content_type(path)

                # Fetch primary file
                content = await get_file_content(client, owner, repo, path, token=token, ref=branch)
                frontmatter = parse_frontmatter(content)

                # For skills, try README.md for description fallback
                description = frontmatter.get("description", "")
                if content_type == "Skill" and not description:
                    try:
                        parts = path.split("/")
                        readme_path = f"{parts[0]}/{parts[1]}/README.md"
                        readme = await get_file_content(client, owner, repo, readme_path, token=token, ref=branch)
                        # Use first non-empty, non-heading line as description
                        for line in readme.splitlines():
                            line = line.strip()
                            if line and not line.startswith("#"):
                                description = line
                                break
                    except httpx.HTTPStatusError:
                        pass  # README is optional

                # Fetch commit metadata
                commit_meta = await get_last_commit(client, owner, repo, path, token=token, ref=branch)

                # Normalise tags and target_ai to lists
                raw_tags = frontmatter.get("tags", [])
                tags: list[str] = raw_tags if isinstance(raw_tags, list) else []
                raw_target_ai = frontmatter.get("target_ai")
                target_ai: list[str] | str | None = raw_target_ai

                item: dict[str, Any] = {
                    "slug": slug,
                    "title": frontmatter.get("title", slug),
                    "description": description or frontmatter.get("description", ""),
                    "content_type": content_type,
                    "tags": json.dumps(tags),
                    "is_public": "true" if frontmatter.get("is_public", False) else "false",
                    "target_ai": json.dumps(target_ai) if target_ai is not None else "",
                    "author": commit_meta.get("author") or "",
                    "last_updated": commit_meta.get("last_updated") or "",
                }
                items.append(item)
                logger.debug("library.sync_content: processed %s (%s)", slug, content_type)

            except Exception:
                logger.exception("library.sync_content: error processing path %s", path)
                # Continue with remaining items — partial sync is better than nothing
                continue

    return items


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="library.sync_content",
    max_retries=3,
    default_retry_delay=2,
)
def sync_library_content(self: Any) -> dict[str, Any]:
    """Fetch all library content from GitHub and write it to Redis.

    On error: retries with exponential backoff (2 ** attempt seconds),
    sets ``library:sync_status = "error:{message}"``, logs a structured error,
    and does NOT delete existing cached items.
    """
    settings = get_settings()

    # Sync Redis client (Celery tasks are synchronous)
    redis_client = sync_redis.from_url(str(settings.REDIS_URL), decode_responses=True)

    redis_client.set(_SYNC_STATUS_KEY, "running")
    logger.info("library.sync_content: starting sync")

    try:
        items = asyncio.run(_fetch_and_build_items(settings))

        # ---------------------------------------------------------------------------
        # Atomic Redis pipeline: rebuild index + write all items
        # ---------------------------------------------------------------------------
        pipe = redis_client.pipeline()
        pipe.delete(_ITEMS_KEY)
        pipe.delete(_PUBLIC_KEY)

        for item in items:
            slug = item["slug"]
            # Build mapping — Redis HSET requires bytes/float/int/str values
            mapping: dict[str, bytes | float | int | str] = {k: v for k, v in item.items() if k != "slug"}
            pipe.hset(f"{_ITEM_PREFIX}{slug}", mapping=mapping)  # type: ignore[arg-type]
            pipe.sadd(_ITEMS_KEY, slug)
            if item.get("is_public") == "true":
                pipe.sadd(_PUBLIC_KEY, slug)

        pipe.set(_LAST_REFRESH_KEY, str(int(time.time())))
        pipe.set(_SYNC_STATUS_KEY, "ok")
        pipe.execute()

        logger.info("library.sync_content: sync complete — %d items written to Redis", len(items))
        return {"status": "ok", "items_synced": len(items)}

    except Exception as exc:
        error_msg = str(exc)
        logger.exception("library.sync_content: sync failed — %s", error_msg)

        # Update status without touching existing item data
        try:
            redis_client.set(_SYNC_STATUS_KEY, f"error:{error_msg[:200]}")
        except Exception as redis_err:
            logger.debug("Could not write sync_status to Redis: %s", redis_err)

        # Exponential backoff: 2^retries seconds
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
