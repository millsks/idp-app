"""Library Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class LibraryItem(BaseModel):
    """Schema for a single library item (no full content field)."""

    slug: str
    title: str
    description: str
    content_type: str
    tags: list[str]
    is_public: bool
    target_ai: str | None = None
    author: str | None = None
    last_updated: datetime | None = None

    model_config = {"from_attributes": True}


class LibraryItemList(BaseModel):
    """Standard list envelope for library items."""

    items: list[LibraryItem]
    total: int
    page: int
    size: int
    pages: int


class LibraryItemDetail(LibraryItem):
    """Schema for a single library item with full content and computed GitHub source URL.

    Extends ``LibraryItem`` by adding the ``content`` field (raw Markdown) and
    ``github_url`` (pre-computed server-side so the frontend never needs to
    know the content repository coordinates).  ``github_url`` is ``None`` when
    the content repository is not configured.
    """

    content: str
    github_url: str | None = None


class LibrarySyncStatus(BaseModel):
    """Response body for the POST /library/refresh endpoint."""

    task_id: str
    status: str
    message: str
