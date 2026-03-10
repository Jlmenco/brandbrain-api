"""
YouTube provider — publica videos via YouTube Data API v3.
Ref: https://developers.google.com/youtube/v3/docs/videos/insert
Nota: YouTube nao suporta posts de texto puro via API (community posts sao limitados).
Este provider faz upload de video com titulo e descricao.
"""
import logging
import tempfile

import httpx

from worker.providers.base import PublishResult, HTTP_TIMEOUT

logger = logging.getLogger("worker.providers.youtube")

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API_BASE = "https://www.googleapis.com/youtube/v3"


def publish_youtube(
    text: str,
    access_token: str,
    video_url: str = "",
    title: str = "",
    tags: list[str] | None = None,
) -> PublishResult:
    """
    Publica video no YouTube.
    Faz download do video_url e upload via resumable upload.
    """
    if not video_url:
        return PublishResult(
            success=False,
            error="YouTube requer um video para publicacao. Adicione media_refs ao conteudo.",
        )

    # Titulo: primeiros 100 chars do texto ou titulo explicito
    video_title = title or text[:100]
    video_tags = tags or []

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    metadata = {
        "snippet": {
            "title": video_title,
            "description": text,
            "tags": video_tags,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            # Step 1: Download video para temp file
            logger.info("Baixando video de %s", video_url)
            video_resp = client.get(video_url)
            video_resp.raise_for_status()
            video_bytes = video_resp.content

            # Step 2: Iniciar resumable upload
            init_resp = client.post(
                f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                json=metadata,
                headers=headers,
            )

            if init_resp.status_code != 200:
                error = f"YouTube init upload {init_resp.status_code}: {init_resp.text[:300]}"
                logger.error(error)
                return PublishResult(success=False, error=error)

            upload_url = init_resp.headers.get("Location", "")
            if not upload_url:
                return PublishResult(success=False, error="YouTube nao retornou upload URL")

            # Step 3: Upload do video
            upload_resp = client.put(
                upload_url,
                content=video_bytes,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/*",
                    "Content-Length": str(len(video_bytes)),
                },
            )

            if upload_resp.status_code in (200, 201):
                data = upload_resp.json()
                video_id = data.get("id", "")
                post_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info("YouTube video publicado: %s", video_id)
                return PublishResult(
                    success=True,
                    provider_post_id=video_id,
                    provider_post_url=post_url,
                )
            else:
                error = f"YouTube upload {upload_resp.status_code}: {upload_resp.text[:300]}"
                logger.error(error)
                return PublishResult(success=False, error=error)

    except httpx.HTTPError as e:
        error = f"YouTube HTTP error: {str(e)}"
        logger.error(error)
        return PublishResult(success=False, error=error)
