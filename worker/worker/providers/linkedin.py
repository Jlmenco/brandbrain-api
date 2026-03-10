"""
LinkedIn provider — publica posts via LinkedIn Marketing API v2.
Usa o endpoint /rest/posts (API versioning header).
Ref: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
"""
import logging

import httpx

from worker.providers.base import PublishResult, HTTP_TIMEOUT

logger = logging.getLogger("worker.providers.linkedin")

API_BASE = "https://api.linkedin.com"
API_VERSION = "202401"


def publish_linkedin(text: str, access_token: str, account_id: str) -> PublishResult:
    """
    Publica um post de texto no LinkedIn.
    account_id = URN do autor (ex: "urn:li:person:abc123" ou "urn:li:organization:123456")
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": API_VERSION,
    }

    payload = {
        "author": account_id,
        "lifecycleState": "PUBLISHED",
        "visibility": "PUBLIC",
        "commentary": text,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
        },
    }

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{API_BASE}/rest/posts",
                json=payload,
                headers=headers,
            )

            if resp.status_code == 201:
                # LinkedIn retorna o ID no header x-restli-id
                post_id = resp.headers.get("x-restli-id", "")
                post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
                logger.info("LinkedIn post publicado: %s", post_id)
                return PublishResult(
                    success=True,
                    provider_post_id=post_id,
                    provider_post_url=post_url,
                )
            else:
                error = f"LinkedIn API {resp.status_code}: {resp.text[:300]}"
                logger.error(error)
                return PublishResult(success=False, error=error)

    except httpx.HTTPError as e:
        error = f"LinkedIn HTTP error: {str(e)}"
        logger.error(error)
        return PublishResult(success=False, error=error)
