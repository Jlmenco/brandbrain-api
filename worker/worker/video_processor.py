"""
Video Processor — processa jobs de geracao de video na fila assincrona.
Executa pipeline: ElevenLabs TTS + Hedra lip-sync por content_item.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select, text

logger = logging.getLogger("worker.video_processor")

STORAGE_BASE = os.getenv("STORAGE_BASE_PATH", "/data/storage")
VIDEOS_DIR = Path(STORAGE_BASE) / "videos"
AVATARS_DIR = Path(STORAGE_BASE) / "avatars"

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George
DEFAULT_MODEL = "eleven_multilingual_v2"

HEDRA_BASE = "https://mercury.dev.dream-ai.com/api"
VIDEO_POLL_INTERVAL = 5
VIDEO_POLL_MAX = 120  # 10 minutos


def poll_video_jobs(session) -> int:
    """Busca content_items com video_job_status='pending' e processa."""
    from sqlalchemy import select as sa_select
    from worker.models import ContentItem

    stmt = (
        sa_select(ContentItem)
        .where(ContentItem.video_job_status == "pending")
        .order_by(ContentItem.updated_at.asc())
        .limit(3)
        .with_for_update(skip_locked=True)
    )

    items = session.execute(stmt).scalars().all()
    if not items:
        return 0

    for item in items:
        item.video_job_status = "processing"
        item.updated_at = datetime.utcnow()
        session.add(item)
    session.commit()

    for item in items:
        asyncio.run(_process_video_job(session, item))

    return len(items)


async def _process_video_job(session, item) -> None:
    """Pipeline completo: avatar + TTS + lip-sync para um content_item."""
    content_id = item.id
    logger.info("Iniciando geracao de video para content_item=%s", content_id)

    try:
        # 1. Buscar avatar do influenciador
        result = session.execute(
            text("""
                SELECT ia.metadata_json, i.voice_id
                FROM influencer_assets ia
                JOIN influencers i ON i.id = ia.influencer_id
                WHERE ia.influencer_id = :inf_id AND ia.asset_type = 'avatar'
                LIMIT 1
            """),
            {"inf_id": item.influencer_id},
        ).first()

        if not result:
            raise RuntimeError("Avatar do influenciador nao encontrado")

        import json
        metadata = result[0] if isinstance(result[0], dict) else json.loads(result[0])
        voice_id = result[1]  # Pode ser None

        avatar_filename = metadata.get("filename", "")
        avatar_path = AVATARS_DIR / avatar_filename
        if not avatar_path.exists():
            raise RuntimeError(f"Arquivo de avatar nao encontrado: {avatar_filename}")

        image_bytes = avatar_path.read_bytes()

        # 2. Gerar voz com ElevenLabs
        audio_bytes = await _generate_speech(item.text[:5000], voice_id=voice_id)

        # 3. Gerar video lip-sync com Hedra
        aspect_map = {
            "tiktok": "9:16",
            "instagram": "9:16",
            "youtube": "16:9",
            "linkedin": "1:1",
            "facebook": "1:1",
        }
        aspect_ratio = aspect_map.get(item.provider_target, "9:16")
        video_bytes = await _generate_video(image_bytes, audio_bytes, aspect_ratio)

        # 4. Salvar video
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        video_filename = f"{content_id}_{uuid.uuid4().hex[:8]}.mp4"
        video_path = VIDEOS_DIR / video_filename
        video_path.write_bytes(video_bytes)

        # 5. Atualizar ContentItem
        media_refs = list(item.media_refs or [])
        media_refs = [m for m in media_refs if m.get("type") != "video"]
        media_refs.append({
            "type": "video",
            "url": f"/content/{content_id}/video",
            "filename": video_filename,
            "source": "hedra",
        })
        item.media_refs = media_refs
        item.video_job_status = "done"
        item.video_job_error = None
        item.updated_at = datetime.utcnow()
        session.add(item)
        session.commit()

        logger.info("Video gerado com sucesso para content_item=%s: %s", content_id, video_filename)

    except Exception as e:
        logger.exception("Erro ao gerar video para content_item=%s: %s", content_id, e)
        item.video_job_status = "failed"
        item.video_job_error = str(e)[:500]
        item.updated_at = datetime.utcnow()
        session.add(item)
        session.commit()


async def _generate_speech(text: str, voice_id: str | None = None) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY nao configurada")

    vid = voice_id or DEFAULT_VOICE_ID
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE}/text-to-speech/{vid}",
            json={
                "text": text,
                "model_id": DEFAULT_MODEL,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            params={"output_format": "mp3_44100_128"},
        )
        resp.raise_for_status()
        return resp.content


async def _generate_video(image_bytes: bytes, audio_bytes: bytes, aspect_ratio: str) -> bytes:
    api_key = os.getenv("HEDRA_API_KEY", "")
    if not api_key:
        raise RuntimeError("HEDRA_API_KEY nao configurada")

    headers = {"X-API-Key": api_key}

    async with httpx.AsyncClient(timeout=30) as client:
        # Upload portrait + audio em paralelo
        portrait_resp, audio_resp = await asyncio.gather(
            client.post(
                f"{HEDRA_BASE}/v1/portrait",
                headers=headers,
                files={"file": ("avatar.png", image_bytes, "image/png")},
            ),
            client.post(
                f"{HEDRA_BASE}/v1/audio",
                headers=headers,
                files={"file": ("speech.mp3", audio_bytes, "audio/mpeg")},
            ),
        )
        portrait_resp.raise_for_status()
        audio_resp.raise_for_status()

        portrait_url = portrait_resp.json()["url"]
        audio_url = audio_resp.json()["url"]

        # Criar job de video
        char_resp = await client.post(
            f"{HEDRA_BASE}/v1/characters",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "avatarImage": portrait_url,
                "voiceUrl": audio_url,
                "audioSource": "audio",
                "aspectRatio": aspect_ratio,
            },
        )
        char_resp.raise_for_status()
        job_id = char_resp.json()["jobId"]

    logger.info("Hedra job iniciado: %s", job_id)

    # Polling ate concluir
    for attempt in range(VIDEO_POLL_MAX):
        await asyncio.sleep(VIDEO_POLL_INTERVAL)
        async with httpx.AsyncClient(timeout=30) as client:
            poll_resp = await client.get(f"{HEDRA_BASE}/v1/projects/{job_id}", headers=headers)
            poll_resp.raise_for_status()
            data = poll_resp.json()

        status = data.get("status")
        video_url = data.get("videoUrl")
        logger.info("Hedra job=%s status=%s attempt=%d", job_id, status, attempt + 1)

        if status == "completed" and video_url:
            async with httpx.AsyncClient(timeout=120) as client:
                dl = await client.get(video_url)
                dl.raise_for_status()
                return dl.content

        if status in ("failed", "error"):
            raise RuntimeError(f"Hedra falhou: {data.get('errorMessage', 'desconhecido')}")

    raise RuntimeError(f"Timeout apos {VIDEO_POLL_MAX * VIDEO_POLL_INTERVAL}s esperando video")
