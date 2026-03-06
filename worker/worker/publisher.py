"""
Publisher — handles the actual posting to social providers.
MVP: mock implementation. Replace with real provider SDKs later.
"""
import logging
import time
from dataclasses import dataclass

from worker.models import ContentItem

logger = logging.getLogger("worker.publisher")


@dataclass
class PublishResult:
    success: bool
    provider_post_id: str = ""
    provider_post_url: str = ""
    error: str = ""


def publish_content(item: ContentItem) -> PublishResult:
    """Dispatch to the appropriate provider publisher."""
    publisher_map = {
        "linkedin": _mock_publish,
        "instagram": _mock_publish,
        "facebook": _mock_publish,
        "x": _mock_publish,
        "tiktok": _mock_publish,
        "youtube": _mock_publish,
    }
    publisher_fn = publisher_map.get(item.provider_target, _mock_publish)
    return publisher_fn(item)


def _mock_publish(item: ContentItem) -> PublishResult:
    """Simulate publishing with a small delay."""
    logger.info(
        "Mock publishing content_item=%s to provider=%s",
        item.id,
        item.provider_target,
    )
    time.sleep(0.3)

    return PublishResult(
        success=True,
        provider_post_id=f"mock_{item.id[:8]}",
        provider_post_url=f"https://{item.provider_target}.com/mock/{item.id[:8]}",
    )
