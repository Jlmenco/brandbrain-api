"""
Scheduler — polls the database for content items due for publishing.
Uses SELECT ... FOR UPDATE SKIP LOCKED for safe multi-instance operation.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, text

from worker.config import settings
from worker.database import get_session
from worker.models import ContentItem, AuditLog
from worker.publisher import publish_content

logger = logging.getLogger("worker.scheduler")


def poll_and_process() -> int:
    """
    Poll for eligible content items and process them one at a time.
    Each item is processed in its own transaction with its own lock.
    Returns the number of items processed.
    """
    processed = 0
    now = datetime.utcnow()

    while processed < settings.BATCH_SIZE:
        with get_session() as session:
            stmt = (
                select(ContentItem)
                .where(
                    # Scheduled items whose time has come
                    (
                        (ContentItem.status == "scheduled")
                        & (ContentItem.scheduled_at <= now)
                    )
                    # Immediate publish requests
                    | (ContentItem.status == "publishing")
                    # Failed items eligible for retry
                    | (
                        (ContentItem.status == "failed")
                        & (ContentItem.retry_count < settings.MAX_RETRIES)
                        & (ContentItem.next_retry_at != None)  # noqa: E711
                        & (ContentItem.next_retry_at <= now)
                    )
                )
                .order_by(ContentItem.scheduled_at.asc().nulls_last())
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            item = session.execute(stmt).scalars().first()
            if item is None:
                break

            _process_item(session, item)
            processed += 1

    return processed


def _process_item(session, item: ContentItem) -> None:
    """Process a single content item: publish and update status."""
    logger.info(
        "Processing content_item=%s status=%s provider=%s retry=%d",
        item.id,
        item.status,
        item.provider_target,
        item.retry_count,
    )

    # Mark as publishing
    item.status = "publishing"
    item.updated_at = datetime.utcnow()
    session.add(item)
    session.flush()

    try:
        result = publish_content(item)

        if result.success:
            item.status = "posted"
            item.posted_at = datetime.utcnow()
            item.provider_post_id = result.provider_post_id
            item.provider_post_url = result.provider_post_url
            item.last_error = None
            item.updated_at = datetime.utcnow()
            logger.info(
                "Published content_item=%s post_id=%s url=%s",
                item.id,
                result.provider_post_id,
                result.provider_post_url,
            )
        else:
            _handle_failure(item, result.error)

    except Exception as e:
        logger.exception("Error publishing content_item=%s: %s", item.id, str(e))
        _handle_failure(item, str(e))

    # Write audit log
    audit = AuditLog(
        org_id=_get_org_id(session, item),
        cost_center_id=item.cost_center_id,
        actor_user_id=None,
        action=f"publish.{'success' if item.status == 'posted' else 'failure'}",
        target_type="content_item",
        target_id=item.id,
        metadata_json={
            "provider": item.provider_target,
            "status": item.status,
            "retry_count": item.retry_count,
            "provider_post_id": item.provider_post_id,
            "error": item.last_error,
        },
    )
    session.add(audit)
    session.add(item)
    session.commit()


def _handle_failure(item: ContentItem, error: str) -> None:
    """Update item for failure with retry backoff calculation."""
    item.retry_count += 1
    item.last_error = error[:500]
    item.updated_at = datetime.utcnow()

    if item.retry_count < settings.MAX_RETRIES:
        delay = settings.RETRY_BASE_DELAY_SECONDS * (
            settings.RETRY_MULTIPLIER ** (item.retry_count - 1)
        )
        item.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        item.status = "failed"
        logger.warning(
            "content_item=%s failed (attempt %d/%d), next retry in %ds",
            item.id,
            item.retry_count,
            settings.MAX_RETRIES,
            delay,
        )
    else:
        item.status = "failed"
        item.next_retry_at = None
        logger.error(
            "content_item=%s permanently failed after %d attempts: %s",
            item.id,
            item.retry_count,
            error,
        )


def _get_org_id(session, item: ContentItem) -> str:
    """Look up org_id from cost_center."""
    result = session.execute(
        text("SELECT org_id FROM cost_centers WHERE id = :cc_id"),
        {"cc_id": item.cost_center_id},
    ).first()
    return result[0] if result else ""
