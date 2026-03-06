from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from worker.scheduler import _handle_failure, _process_item, _get_org_id
from worker.publisher import PublishResult
from worker.config import settings


class TestHandleFailure:
    def test_first_failure_increments_retry(self, content_item):
        content_item.retry_count = 0
        _handle_failure(content_item, "Connection timeout")

        assert content_item.retry_count == 1
        assert content_item.last_error == "Connection timeout"
        assert content_item.status == "failed"
        assert content_item.next_retry_at is not None

    def test_backoff_first_retry(self, content_item):
        content_item.retry_count = 0
        before = datetime.utcnow()
        _handle_failure(content_item, "Error")

        # First retry: 30s base delay * 4^0 = 30s
        expected_delay = settings.RETRY_BASE_DELAY_SECONDS
        expected_time = before + timedelta(seconds=expected_delay)
        assert content_item.next_retry_at is not None
        # Allow 2s tolerance
        diff = abs((content_item.next_retry_at - expected_time).total_seconds())
        assert diff < 2

    def test_backoff_second_retry(self, content_item):
        content_item.retry_count = 1
        before = datetime.utcnow()
        _handle_failure(content_item, "Error")

        # Second retry: 30 * 4^1 = 120s
        expected_delay = settings.RETRY_BASE_DELAY_SECONDS * settings.RETRY_MULTIPLIER
        expected_time = before + timedelta(seconds=expected_delay)
        assert content_item.next_retry_at is not None
        diff = abs((content_item.next_retry_at - expected_time).total_seconds())
        assert diff < 2

    def test_backoff_third_retry(self, content_item):
        content_item.retry_count = 2
        before = datetime.utcnow()
        _handle_failure(content_item, "Error")

        # Third retry: 30 * 4^2 = 480s — but this is attempt 3 = MAX_RETRIES
        # So it should be permanently failed with no next_retry
        assert content_item.retry_count == 3
        assert content_item.status == "failed"
        assert content_item.next_retry_at is None

    def test_max_retries_permanent_failure(self, content_item):
        content_item.retry_count = settings.MAX_RETRIES - 1
        _handle_failure(content_item, "Final error")

        assert content_item.retry_count == settings.MAX_RETRIES
        assert content_item.status == "failed"
        assert content_item.next_retry_at is None

    def test_error_truncated_to_500_chars(self, content_item):
        content_item.retry_count = 0
        long_error = "x" * 1000
        _handle_failure(content_item, long_error)

        assert len(content_item.last_error) == 500


class TestProcessItem:
    @patch("worker.scheduler.publish_content")
    @patch("worker.scheduler._get_org_id", return_value="org-test")
    def test_success(self, mock_org, mock_publish, content_item):
        mock_publish.return_value = PublishResult(
            success=True,
            provider_post_id="post_123",
            provider_post_url="https://linkedin.com/post/123",
        )
        session = MagicMock()

        _process_item(session, content_item)

        assert content_item.status == "posted"
        assert content_item.provider_post_id == "post_123"
        assert content_item.provider_post_url == "https://linkedin.com/post/123"
        assert content_item.posted_at is not None
        assert content_item.last_error is None
        session.commit.assert_called_once()

    @patch("worker.scheduler.publish_content")
    @patch("worker.scheduler._get_org_id", return_value="org-test")
    def test_publish_failure(self, mock_org, mock_publish, content_item):
        mock_publish.return_value = PublishResult(
            success=False,
            error="API rate limit",
        )
        session = MagicMock()

        _process_item(session, content_item)

        assert content_item.status == "failed"
        assert content_item.retry_count == 1
        assert content_item.last_error == "API rate limit"
        session.commit.assert_called_once()

    @patch("worker.scheduler.publish_content")
    @patch("worker.scheduler._get_org_id", return_value="org-test")
    def test_publish_exception(self, mock_org, mock_publish, content_item):
        mock_publish.side_effect = Exception("Network down")
        session = MagicMock()

        _process_item(session, content_item)

        assert content_item.status == "failed"
        assert content_item.retry_count == 1
        assert "Network down" in content_item.last_error
        session.commit.assert_called_once()

    @patch("worker.scheduler.publish_content")
    @patch("worker.scheduler._get_org_id", return_value="org-test")
    def test_audit_log_created(self, mock_org, mock_publish, content_item):
        mock_publish.return_value = PublishResult(success=True, provider_post_id="p1")
        session = MagicMock()

        _process_item(session, content_item)

        # session.add called for: flush(item), audit_log, item final
        add_calls = session.add.call_args_list
        assert len(add_calls) >= 2  # item + audit log


class TestGetOrgId:
    def test_returns_org_id(self, content_item):
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.__getitem__ = MagicMock(return_value="org-123")
        session.execute.return_value.first.return_value = mock_result

        org_id = _get_org_id(session, content_item)
        assert org_id == "org-123"

    def test_returns_empty_when_not_found(self, content_item):
        session = MagicMock()
        session.execute.return_value.first.return_value = None

        org_id = _get_org_id(session, content_item)
        assert org_id == ""
