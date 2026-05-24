"""Celery application factory and example tasks.

Usage:
    pixi run backend-worker   — start a Celery worker
    pixi run backend-beat     — start the periodic scheduler
    pixi run backend-flower   — start the Flower monitoring UI
"""

from celery import Celery
from celery.utils.log import get_task_logger

from idp_app.core.config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = Celery("idp_app")

app.config_from_object(
    {
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        "task_always_eager": settings.CELERY_TASK_ALWAYS_EAGER,
        # Serialisation
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        # Timezone
        "timezone": "UTC",
        "enable_utc": True,
        # Worker settings
        "worker_prefetch_multiplier": 1,
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        # Result expiry (24 hours)
        "result_expires": 86400,
    }
)

# Auto-discover tasks in all installed apps
app.autodiscover_tasks(["idp_app.tasks"])

# ---------------------------------------------------------------------------
# Example tasks
# ---------------------------------------------------------------------------


@app.task(bind=True, name="idp_app.tasks.send_welcome_email")  # type: ignore[untyped-decorator]
def send_welcome_email(self: Celery, user_id: int, email: str) -> dict[str, str]:
    """Send a welcome email to a newly registered user (stub)."""
    logger.info("Sending welcome email to %s (user_id=%d)", email, user_id)
    # TODO: integrate with an email service (SendGrid, SES, etc.)
    return {"status": "queued", "user_id": str(user_id), "email": email}


@app.task(bind=True, name="idp_app.tasks.cleanup_expired_tokens")  # type: ignore[untyped-decorator]
def cleanup_expired_tokens(self: Celery) -> dict[str, int]:
    """Periodic task: remove expired JWT refresh tokens from the database."""
    logger.info("Cleaning up expired tokens…")
    # TODO: query the database and delete expired tokens
    deleted_count = 0
    return {"deleted": deleted_count}
