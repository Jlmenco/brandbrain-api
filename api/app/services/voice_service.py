"""ElevenLabs Text-to-Speech service."""

import httpx
from app.config import settings

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
# Voz padrao: "George" (masculina, profissional) — pode ser configuravel por influenciador
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL = "eleven_multilingual_v2"


class VoiceService:
    """Gera audio a partir de texto usando ElevenLabs TTS."""

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY

    async def generate_speech(
        self,
        text: str,
        voice_id: str | None = None,
        model_id: str | None = None,
    ) -> bytes:
        """Converte texto em audio MP3.

        Args:
            text: Texto a ser convertido em fala.
            voice_id: ID da voz no ElevenLabs (opcional, usa padrao).
            model_id: Modelo TTS (opcional, usa eleven_multilingual_v2).

        Returns:
            Bytes do audio MP3.
        """
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY nao configurada")

        vid = voice_id or DEFAULT_VOICE_ID
        url = f"{ELEVENLABS_BASE}/text-to-speech/{vid}"

        payload = {
            "text": text,
            "model_id": model_id or DEFAULT_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                params={"output_format": "mp3_44100_128"},
            )
            resp.raise_for_status()
            return resp.content

    async def list_voices(self) -> list[dict]:
        """Lista vozes disponiveis no ElevenLabs."""
        if not self.api_key:
            return []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ELEVENLABS_BASE}/voices",
                headers={"xi-api-key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "voice_id": v["voice_id"],
                    "name": v["name"],
                    "labels": v.get("labels", {}),
                }
                for v in data.get("voices", [])
            ]
