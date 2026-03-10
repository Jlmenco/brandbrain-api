"""Testes unitarios para os providers reais (com HTTP mockado)."""
from unittest.mock import patch, MagicMock

from worker.providers.linkedin import publish_linkedin
from worker.providers.meta import publish_facebook, publish_instagram
from worker.providers.tiktok import publish_tiktok
from worker.providers.youtube import publish_youtube
from worker.providers.base import PublishResult


class TestLinkedIn:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.headers = {"x-restli-id": "urn:li:share:123456"}

        with patch("worker.providers.linkedin.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = mock_resp

            result = publish_linkedin("Texto teste", "token123", "urn:li:person:abc")
            assert result.success is True
            assert result.provider_post_id == "urn:li:share:123456"
            assert "linkedin.com" in result.provider_post_url

    def test_failure(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"

        with patch("worker.providers.linkedin.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = mock_resp

            result = publish_linkedin("Texto", "bad_token", "urn:li:person:abc")
            assert result.success is False
            assert "403" in result.error


class TestFacebook:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "123_456"}

        with patch("worker.providers.meta.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = mock_resp

            result = publish_facebook("Post teste", "token", "page123")
            assert result.success is True
            assert result.provider_post_id == "123_456"

    def test_failure(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": {"message": "Invalid token"}}

        with patch("worker.providers.meta.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = mock_resp

            result = publish_facebook("Post", "bad", "page123")
            assert result.success is False
            assert "Invalid token" in result.error


class TestInstagram:
    def test_requires_image(self):
        result = publish_instagram("Caption", "token", "ig123")
        assert result.success is False
        assert "imagem" in result.error

    def test_success(self):
        create_resp = MagicMock()
        create_resp.json.return_value = {"id": "container123"}
        publish_resp = MagicMock()
        publish_resp.json.return_value = {"id": "post789"}

        with patch("worker.providers.meta.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.side_effect = [create_resp, publish_resp]

            result = publish_instagram("Caption", "token", "ig123", image_url="https://example.com/img.jpg")
            assert result.success is True
            assert result.provider_post_id == "post789"


class TestTikTok:
    def test_requires_media(self):
        result = publish_tiktok("Texto", "token")
        assert result.success is False
        assert "video ou imagens" in result.error

    def test_photo_post_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "error": {"code": "ok"},
            "data": {"publish_id": "pub123"},
        }

        with patch("worker.providers.tiktok.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = mock_resp

            result = publish_tiktok("Texto", "token", photo_urls=["https://example.com/1.jpg"])
            assert result.success is True
            assert result.provider_post_id == "pub123"


class TestYouTube:
    def test_requires_video(self):
        result = publish_youtube("Texto", "token")
        assert result.success is False
        assert "video" in result.error

    def test_success(self):
        video_resp = MagicMock()
        video_resp.content = b"fake_video_bytes"
        video_resp.raise_for_status = MagicMock()

        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.headers = {"Location": "https://upload.example.com/upload"}

        upload_resp = MagicMock()
        upload_resp.status_code = 200
        upload_resp.json.return_value = {"id": "vid_abc123"}

        with patch("worker.providers.youtube.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = video_resp
            mock_client.return_value.post.return_value = init_resp
            mock_client.return_value.put.return_value = upload_resp

            result = publish_youtube("Video titulo", "token", video_url="https://example.com/video.mp4")
            assert result.success is True
            assert result.provider_post_id == "vid_abc123"
            assert "youtube.com" in result.provider_post_url
