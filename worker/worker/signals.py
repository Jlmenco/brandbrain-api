"""
Redis Pub/Sub listener for immediate publish signals.
Runs in a daemon thread alongside the main poll loop.
"""
import logging
import threading
import time

import redis

from worker.config import settings

logger = logging.getLogger("worker.signals")

CHANNEL = "bb:publish_signal"


class SignalListener:
    """Listens for Redis publish signals and triggers immediate poll cycles."""

    def __init__(self, on_signal_callback):
        self._callback = on_signal_callback
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        """Start the listener in a daemon thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._listen, daemon=True, name="signal-listener"
        )
        self._thread.start()
        logger.info("Signal listener started on channel %s", CHANNEL)

    def stop(self):
        self._running = False

    def _listen(self):
        """Subscribe to Redis channel and invoke callback on messages."""
        while self._running:
            try:
                r = redis.from_url(settings.REDIS_URL)
                pubsub = r.pubsub()
                pubsub.subscribe(CHANNEL)

                for message in pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] == "message":
                        content_item_id = message["data"]
                        if isinstance(content_item_id, bytes):
                            content_item_id = content_item_id.decode("utf-8")
                        logger.info(
                            "Received publish signal for content_item=%s",
                            content_item_id,
                        )
                        self._callback(content_item_id)

                pubsub.close()
                r.close()
            except redis.ConnectionError:
                logger.warning("Redis connection lost, reconnecting in 5s...")
                time.sleep(5)
            except Exception:
                logger.exception("Signal listener error, restarting in 5s...")
                time.sleep(5)
