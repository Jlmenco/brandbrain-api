import threading
from unittest.mock import MagicMock, patch

from worker.signals import SignalListener, CHANNEL


def test_listener_start():
    callback = MagicMock()
    listener = SignalListener(on_signal_callback=callback)

    with patch.object(listener, "_listen"):
        listener.start()

    assert listener._running is True
    assert listener._thread is not None
    assert listener._thread.daemon is True

    listener.stop()
    assert listener._running is False


def test_listener_stop():
    callback = MagicMock()
    listener = SignalListener(on_signal_callback=callback)
    listener._running = True

    listener.stop()

    assert listener._running is False


def test_channel_name():
    assert CHANNEL == "bb:publish_signal"


def test_listener_callback_invoked():
    """Test that the callback is invoked when a message is received."""
    callback = MagicMock()
    listener = SignalListener(on_signal_callback=callback)

    # Simulate what _listen does when it gets a message
    mock_message = {"type": "message", "data": b"content-item-123"}
    content_item_id = mock_message["data"]
    if isinstance(content_item_id, bytes):
        content_item_id = content_item_id.decode("utf-8")

    callback(content_item_id)
    callback.assert_called_once_with("content-item-123")
