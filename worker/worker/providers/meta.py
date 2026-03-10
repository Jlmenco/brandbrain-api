"""
Meta provider — publica no Facebook e Instagram via Graph API.
Facebook: POST /{page-id}/feed
Instagram: POST /{ig-user-id}/media + POST /{ig-user-id}/media_publish
Ref: https://developers.facebook.com/docs/graph-api/reference/page/feed
Ref: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing
"""
import logging

import httpx

from worker.providers.base import PublishResult, HTTP_TIMEOUT

logger = logging.getLogger("worker.providers.meta")

GRAPH_API = "https://graph.facebook.com/v21.0"


def publish_facebook(text: str, access_token: str, page_id: str) -> PublishResult:
    """Publica um post de texto em uma pagina do Facebook."""
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{GRAPH_API}/{page_id}/feed",
                data={
                    "message": text,
                    "access_token": access_token,
                },
            )
            data = resp.json()

            if "id" in data:
                post_id = data["id"]
                post_url = f"https://www.facebook.com/{post_id}"
                logger.info("Facebook post publicado: %s", post_id)
                return PublishResult(
                    success=True,
                    provider_post_id=post_id,
                    provider_post_url=post_url,
                )
            else:
                error_msg = data.get("error", {}).get("message", resp.text[:300])
                error = f"Facebook API error: {error_msg}"
                logger.error(error)
                return PublishResult(success=False, error=error)

    except httpx.HTTPError as e:
        error = f"Facebook HTTP error: {str(e)}"
        logger.error(error)
        return PublishResult(success=False, error=error)


def publish_instagram(text: str, access_token: str, ig_user_id: str, image_url: str = "") -> PublishResult:
    """
    Publica no Instagram.
    Instagram requer midia (imagem ou video). Se image_url nao for fornecida,
    publica como caption-only (requer imagem placeholder ou falha).
    """
    if not image_url:
        return PublishResult(
            success=False,
            error="Instagram requer uma imagem para publicacao. Adicione media_refs ao conteudo.",
        )

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            # Step 1: Criar container de midia
            create_resp = client.post(
                f"{GRAPH_API}/{ig_user_id}/media",
                data={
                    "image_url": image_url,
                    "caption": text,
                    "access_token": access_token,
                },
            )
            create_data = create_resp.json()

            if "id" not in create_data:
                error_msg = create_data.get("error", {}).get("message", create_resp.text[:300])
                return PublishResult(success=False, error=f"Instagram create media error: {error_msg}")

            container_id = create_data["id"]

            # Step 2: Publicar o container
            publish_resp = client.post(
                f"{GRAPH_API}/{ig_user_id}/media_publish",
                data={
                    "creation_id": container_id,
                    "access_token": access_token,
                },
            )
            publish_data = publish_resp.json()

            if "id" in publish_data:
                post_id = publish_data["id"]
                post_url = f"https://www.instagram.com/p/{post_id}/"
                logger.info("Instagram post publicado: %s", post_id)
                return PublishResult(
                    success=True,
                    provider_post_id=post_id,
                    provider_post_url=post_url,
                )
            else:
                error_msg = publish_data.get("error", {}).get("message", publish_resp.text[:300])
                error = f"Instagram publish error: {error_msg}"
                logger.error(error)
                return PublishResult(success=False, error=error)

    except httpx.HTTPError as e:
        error = f"Instagram HTTP error: {str(e)}"
        logger.error(error)
        return PublishResult(success=False, error=error)
