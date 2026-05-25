"""GitHub Content API client for the library sync service.

Provides async functions for fetching and parsing content from a GitHub
repository.  All HTTP calls use ``httpx.AsyncClient`` with a bearer token.

Rate-limit awareness: after every response the ``X-RateLimit-Remaining``
header is checked against ``X-RateLimit-Limit``.  When remaining usage
reaches 80 % or above, a structured warning is logged so an operator can
act before the limit is hit.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx
import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_RATE_WARN_THRESHOLD = 0.80  # log warning when 80 % of quota is consumed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _check_rate_limit(response: httpx.Response) -> None:
    """Log a warning when the GitHub rate-limit is 80 % consumed."""
    try:
        remaining = int(response.headers.get("X-RateLimit-Remaining", -1))
        limit = int(response.headers.get("X-RateLimit-Limit", -1))
        if limit > 0 and remaining >= 0:
            consumed_pct = 1.0 - (remaining / limit)
            if consumed_pct >= _RATE_WARN_THRESHOLD:
                logger.warning(
                    "GitHub rate limit warning: %d / %d requests remaining (%.0f%% consumed)",
                    remaining,
                    limit,
                    consumed_pct * 100,
                )
    except (ValueError, TypeError):
        pass  # defensive — never crash on header parsing


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def get_file_tree(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    branch: str,
    *,
    token: str,
) -> list[str]:
    """Return paths in *repo* matching skill or prompt patterns.

    Uses the GitHub Git Trees API (recursive) to fetch the full tree in a
    single request.  Returns only paths that match:
    - ``skills/{slug}/SKILL.md``
    - ``prompts/{slug}.md``
    """
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}"
    response = await client.get(
        url,
        headers=_auth_headers(token),
        params={"recursive": "1"},
    )
    _check_rate_limit(response)
    response.raise_for_status()

    tree: list[dict[str, Any]] = response.json().get("tree", [])

    skill_pattern = re.compile(r"^skills/[^/]+/SKILL\.md$")
    prompt_pattern = re.compile(r"^prompts/[^/]+\.md$")

    return [
        item["path"]
        for item in tree
        if item.get("type") == "blob" and (skill_pattern.match(item["path"]) or prompt_pattern.match(item["path"]))
    ]


async def get_file_content(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    *,
    token: str,
    ref: str = "main",
) -> str:
    """Fetch and decode the contents of a file from GitHub.

    Uses the GitHub Contents API.  Returns the decoded UTF-8 string.

    Raises :exc:`httpx.HTTPStatusError` on non-2xx responses.
    """
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    response = await client.get(
        url,
        headers=_auth_headers(token),
        params={"ref": ref},
    )
    _check_rate_limit(response)
    response.raise_for_status()

    payload = response.json()
    encoded = payload.get("content", "")
    # GitHub returns content split over multiple lines; strip whitespace
    decoded = base64.b64decode(encoded.replace("\n", "")).decode("utf-8")
    return decoded


async def get_last_commit(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    *,
    token: str,
    ref: str = "main",
) -> dict[str, str | None]:
    """Return ``{author, last_updated}`` from the most recent commit touching *path*.

    ``author`` is the committer's GitHub login (or display name).
    ``last_updated`` is the ISO-8601 commit date string.

    Returns ``{"author": None, "last_updated": None}`` when no commits are found.
    """
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/commits"
    response = await client.get(
        url,
        headers=_auth_headers(token),
        params={"path": path, "sha": ref, "per_page": "1"},
    )
    _check_rate_limit(response)
    response.raise_for_status()

    commits: list[dict[str, Any]] = response.json()
    if not commits:
        return {"author": None, "last_updated": None}

    commit = commits[0]
    # Prefer the committer login; fall back to author name inside the commit object
    author: str | None = (commit.get("committer") or {}).get("login") or (
        commit.get("commit", {}).get("committer") or {}
    ).get("name")
    last_updated: str | None = (commit.get("commit", {}).get("committer") or {}).get("date")
    return {"author": author, "last_updated": last_updated}


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Extract and parse YAML frontmatter from a Markdown string.

    Frontmatter is the content between the first two ``---`` delimiters at
    the top of the file.  Returns an empty dict when no frontmatter is found
    or when parsing fails.
    """
    stripped = content.strip()
    if not stripped.startswith("---"):
        return {}

    # Find the closing delimiter (must be on its own line, after the opening)
    rest = stripped[3:]
    end_idx = rest.find("\n---")
    if end_idx == -1:
        return {}

    yaml_block = rest[:end_idx].strip()
    try:
        parsed = yaml.safe_load(yaml_block)
        return parsed if isinstance(parsed, dict) else {}
    except yaml.YAMLError:
        logger.warning("Failed to parse frontmatter YAML: %s…", yaml_block[:120])
        return {}


def derive_content_type(path: str) -> str:
    """Return ``'Skill'`` for skill paths, ``'Prompt'`` for prompt paths."""
    if path.startswith("skills/"):
        return "Skill"
    return "Prompt"


def derive_slug(path: str) -> str:
    """Extract the slug from a skill or prompt path.

    ``skills/my-skill/SKILL.md`` → ``my-skill``
    ``prompts/my-prompt.md``     → ``my-prompt``
    """
    parts = path.split("/")
    if path.startswith("skills/") and len(parts) >= 2:
        return parts[1]
    if path.startswith("prompts/") and len(parts) == 2:
        return parts[1].removesuffix(".md")
    return path
