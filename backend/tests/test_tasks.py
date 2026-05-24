"""Tests for the Celery task module."""

from idp_app.tasks.worker import app as celery_app
from idp_app.tasks.worker import cleanup_expired_tokens, send_welcome_email


class TestCeleryApp:
    def test_app_name(self) -> None:
        assert celery_app.main == "idp_app"

    def test_registered_tasks(self) -> None:
        task_names = list(celery_app.tasks.keys())
        assert any("send_welcome_email" in name for name in task_names)
        assert any("cleanup_expired_tokens" in name for name in task_names)


class TestSendWelcomeEmail:
    def test_returns_expected_keys(self) -> None:
        # .apply() runs the task synchronously in-process; Celery automatically
        # passes the task instance as `self` for bind=True tasks.
        result = send_welcome_email.apply(kwargs={"user_id": 1, "email": "test@example.com"}).get()
        assert result["status"] == "queued"
        assert result["user_id"] == "1"
        assert result["email"] == "test@example.com"


class TestCleanupExpiredTokens:
    def test_returns_deleted_count(self) -> None:
        result = cleanup_expired_tokens.apply().get()
        assert "deleted" in result
        assert isinstance(result["deleted"], int)
        assert result["deleted"] == 0
