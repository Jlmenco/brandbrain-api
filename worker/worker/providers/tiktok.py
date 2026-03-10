"""
TikTok provider — publica via Content Posting API.
Ref: https://developers.tiktok.com/doc/content-posting-api-get-started
Nota: TikTok Content Posting API suporta apenas video.
Para texto/imagem, usa-se o Photo Post (photo mode).
"""
import logging

import httpx

from worker.providers.base import PublishResult, HTTP_TIMEOUT

logger = logging.getLogger("worker.providers.tiktok")

API_BASE = "https://open.tiktokapis.com/v2"


def publish_tiktok(text: str, access_token: str, video_url: str = "", photo_urls: list[str] | None = None) -> PublishResult:
    """
    Publica no TikTok.
    Suporta:
    - Photo post (1-35 imagens + caption)
    - Video por URL (PULL_FROM_URL)
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    if photo_urls:
        # Photo post mode
        return _publish_photo_post(text, headers, photo_urls)
    elif video_url:
        # Video post mode (PULL_FROM_URL)
        return _publish_video_post(text, headers, video_url)
    else:
        return PublishResult(
            success=False,
            error="TikTok requer video ou imagens. Adicione media_refs ao conteudo.",
        )


def _publish_photo_post(text: str, headers: dict, photo_urls: list[str]) -> PublishResult:
    """Publica foto post no TikTok (1-35 imagens)."""
    payload = {
        "post_info": {
            "title": text[:150],
            "description": text,
            "disable_comment": False,
            "privacy_level": "PUBLIC_TO_EVERYONE",
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_images": photo_urls[:35],
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO",
    }

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{API_BASE}/post/publish/",
                json=payload,
                headers=headers,
            )
            data = resp.json()

            if data.get("error", {}).get("code") == "ok":
                publish_id = data.get("data", {}).get("publish_id", "")
                logger.info("TikTok photo post publicado: %s", publish_id)
                return PublishResult(
                    success=True,
                    provider_post_id=publish_id,
                    provider_post_url=f"https://www.tiktok.com/@me/photo/{publish_id}",
                )
            else:
                error_msg = data.get("error", {}).get("message", resp.text[:300])
                error = f"TikTok API error: {error_msg}"
                logger.error(error)
                return PublishResult(success=False, error=error)

    except httpx.HTTPError as e:
        error = f"TikTok HTTP error: {str(e)}"
        logger.error(error)
        return PublishResult(success=False, error=error)


def _publish_video_post(text: str, headers: dict, video_url: str) -> PublishResult:
    """Publica video no TikTok via PULL_FROM_URL."""
    payload = {
        "post_info": {
            "title": text[:150],
            "description": text,
            "disable_comment": False,
            "privacy_level": "PUBLIC_TO_EVERYONE",
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
        "post_mode": "DIRECT_POST",
        "media_type": "VIDEO",
    }

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{API_BASE}/post/publish/",
                json=payload,
                headers=headers,
            )
            data = resp.json()

            if data.get("error", {}).get("code") == "ok":
                publish_id = data.get("data", {}).get("publish_id", "")
                logger.info("TikTok video publicado: %s", publish_id)
                return PublishResult(
                    success=True,
                    provider_post_id=publish_id,
                    provider_post_url=f"https://www.tiktok.com/@me/video/{publish_id}",
                )
            else:
                error_msg = data.get("error", {}).get("message", resp.text[:300])
                error = f"TikTok API error: {error_msg}"
                logger.error(error)
                return PublishResult(success=False, error=error)

    except httpx.HTTPError as e:
        error = f"TikTok HTTP error: {str(e)}"
        logger.error(error)
        return PublishResult(success=False, error=error)
