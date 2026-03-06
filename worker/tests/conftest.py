import uuid
from datetime import datetime, timedelta

import pytest

from worker.models import ContentItem


@pytest.fixture
def make_content_item():
    """Factory fixture to create ContentItem instances with defaults."""

    def _make(**overrides):
        defaults = {
            "id": str(uuid.uuid4()),
            "cost_center_id": "cc-test",
            "influencer_id": "inf-test",
            "provider_target": "linkedin",
            "text": "Test content",
            "status": "publishing",
            "scheduled_at": datetime.utcnow(),
            "retry_count": 0,
            "next_retry_at": None,
            "last_error": None,
            "version": 1,
        }
        defaults.update(overrides)
        return ContentItem(**defaults)

    return _make


@pytest.fixture
def content_item(make_content_item):
    return make_content_item()


@pytest.fixture
def scheduled_item(make_content_item):
    return make_content_item(
        status="scheduled",
        scheduled_at=datetime.utcnow() - timedelta(minutes=1),
    )


@pytest.fixture
def failed_item(make_content_item):
    return make_content_item(
        status="failed",
        retry_count=1,
        last_error="Previous error",
        next_retry_at=datetime.utcnow() - timedelta(minutes=1),
    )
