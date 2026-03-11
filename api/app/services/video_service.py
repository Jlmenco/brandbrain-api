"""Hedra lip-sync video generation service."""

import asyncio
import logging

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

HEDRA_BASE = "https://mercury.dev.dream-ai.com/api"
HEDRA_TIMEOUT = 30
VIDEO_POLL_INTERVAL = 5  # seconds
VIDEO_POLL_MAX_ATTEMPTS = 120  # 10 minutes max


class VideoService:
    """Gera videos lip-sync usando Hedra Character API."""

    def __init__(self):
        self.api_key = settings.HEDRA_API_KEY

    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
        }

    async def upload_portrait(self, image_bytes: bytes, filename: str = "avatar.png") -> str:
        """Upload imagem do avatar para Hedra.

        Returns:
            URL da imagem no Hedra.
        """
        async with httpx.AsyncClient(timeout=HEDRA_TIMEOUT) as client:
            resp = await client.post(
                f"{HEDRA_BASE}/v1/portrait",
                headers=self._headers(),
                files={"file": (filename, image_bytes, "image/png")},
            )
            resp.raise_for_status()
            return resp.json()["url"]

    async def upload_audio(self, audio_bytes: bytes, filename: str = "speech.mp3") -> str:
        """Upload audio para Hedra.

        Returns:
            URL do audio no Hedra.
        """
        async with httpx.AsyncClient(timeout=HEDRA_TIMEOUT) as client:
            resp = await client.post(
                f"{HEDRA_BASE}/v1/audio",
                headers=self._headers(),
                files={"file": (filename, audio_bytes, "audio/mpeg")},
            )
            resp.raise_for_status()
            return resp.json()["url"]

    async def create_character_video(
        self,
        portrait_url: str,
        audio_url: str,
        aspect_ratio: str = "9:16",
    ) -> str:
        """Inicia geracao de video lip-sync.

        Args:
            portrait_url: URL da imagem (retornada por upload_portrait).
            audio_url: URL do audio (retornada por upload_audio).
            aspect_ratio: "9:16" (vertical), "16:9" (horizontal), "1:1" (quadrado).

        Returns:
            job_id para polling.
        """
        async with httpx.AsyncClient(timeout=HEDRA_TIMEOUT) as client:
            resp = await client.post(
                f"{HEDRA_BASE}/v1/characters",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={
                    "avatarImage": portrait_url,
                    "voiceUrl": audio_url,
                    "audioSource": "audio",
                    "aspectRatio": aspect_ratio,
                },
            )
            resp.raise_for_status()
            return resp.json()["jobId"]

    async def poll_project(self, job_id: str) -> dict:
        """Consulta status de um projeto/video.

        Returns:
            Dict com status, progress, video_url, error_message.
        """
        async with httpx.AsyncClient(timeout=HEDRA_TIMEOUT) as client:
            resp = await client.get(
                f"{HEDRA_BASE}/v1/projects/{job_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status"),
                "progress": data.get("progress"),
                "video_url": data.get("videoUrl"),
                "error_message": data.get("errorMessage"),
            }

    async def wait_for_video(self, job_id: str) -> str:
        """Aguarda ate o video estar pronto.

        Returns:
            URL do video finalizado.

        Raises:
            RuntimeError: Se falhar ou timeout.
        """
        for attempt in range(VIDEO_POLL_MAX_ATTEMPTS):
            project = await self.poll_project(job_id)
            status = project["status"]

            if status == "completed" and project["video_url"]:
                return project["video_url"]

            if status in ("failed", "error"):
                raise RuntimeError(
                    f"Video generation failed: {project.get('error_message', 'unknown error')}"
                )

            logger.info(
                "Video %s: status=%s progress=%s (attempt %d/%d)",
                job_id, status, project.get("progress"), attempt + 1, VIDEO_POLL_MAX_ATTEMPTS,
            )
            await asyncio.sleep(VIDEO_POLL_INTERVAL)

        raise RuntimeError(f"Video generation timeout after {VIDEO_POLL_MAX_ATTEMPTS * VIDEO_POLL_INTERVAL}s")

    async def download_video(self, video_url: str) -> bytes:
        """Baixa o video finalizado.

        Returns:
            Bytes do video MP4.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(video_url)
            resp.raise_for_status()
            return resp.content

    async def generate_talking_video(
        self,
        image_bytes: bytes,
        audio_bytes: bytes,
        aspect_ratio: str = "9:16",
    ) -> tuple[str, bytes]:
        """Pipeline completo: upload image + audio → gerar video → download.

        Args:
            image_bytes: Imagem do avatar (PNG/JPG).
            audio_bytes: Audio da fala (MP3).
            aspect_ratio: Proporcao do video.

        Returns:
            Tuple (video_url, video_bytes).
        """
        if not self.api_key:
            raise RuntimeError("HEDRA_API_KEY nao configurada")

        # 1. Upload assets
        portrait_url, audio_url = await asyncio.gather(
            self.upload_portrait(image_bytes),
            self.upload_audio(audio_bytes),
        )

        # 2. Start generation
        job_id = await self.create_character_video(portrait_url, audio_url, aspect_ratio)
        logger.info("Video generation started: job_id=%s", job_id)

        # 3. Wait for completion
        video_url = await self.wait_for_video(job_id)
        logger.info("Video ready: %s", video_url)

        # 4. Download
        video_bytes = await self.download_video(video_url)

        return video_url, video_bytes
