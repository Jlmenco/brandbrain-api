"""
Brand Brain Worker — Scheduler + Publisher.

Responsibilities:
- Poll for scheduled content items whose scheduled_at has passed
- Process immediate publish requests signaled via Redis
- Retry failed publish attempts with exponential backoff
- Log all publish events to audit_logs
"""
import logging
import signal
import sys
import threading

from worker.config import settings
from worker.scheduler import poll_and_process
from worker.signals import SignalListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("worker")

_wake_event = threading.Event()
_shutdown = False


def _on_publish_signal(content_item_id: str):
    """Called by SignalListener when an immediate publish is requested."""
    logger.info("Waking poll loop for immediate publish: %s", content_item_id)
    _wake_event.set()


def _handle_shutdown(signum, frame):
    global _shutdown
    logger.info("Received shutdown signal (%s), exiting gracefully...", signum)
    _shutdown = True
    _wake_event.set()


def main():
    global _shutdown

    logger.info("Brand Brain Worker starting")
    logger.info("  DATABASE_URL: %s...", settings.DATABASE_URL[:40])
    logger.info("  REDIS_URL: %s", settings.REDIS_URL)
    logger.info("  POLL_INTERVAL: %ds", settings.POLL_INTERVAL_SECONDS)
    logger.info("  MAX_RETRIES: %d", settings.MAX_RETRIES)
    logger.info("  BATCH_SIZE: %d", settings.BATCH_SIZE)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    listener = SignalListener(on_signal_callback=_on_publish_signal)
    listener.start()

    logger.info("Worker ready. Entering poll loop.")

    while not _shutdown:
        try:
            processed = poll_and_process()
            if processed > 0:
                logger.info("Poll cycle complete: processed %d items", processed)
        except Exception:
            logger.exception("Error in poll cycle")

        _wake_event.wait(timeout=settings.POLL_INTERVAL_SECONDS)
        _wake_event.clear()

    listener.stop()
    logger.info("Worker shut down cleanly.")


if __name__ == "__main__":
    main()
