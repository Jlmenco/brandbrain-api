"""
Publisher — despacha publicacao para o provider real ou mock.
Busca credenciais do SocialAccount no DB e chama o provider adequado.
"""
import base64
import hashlib
import logging
import os
import time

from cryptography.fernet import Fernet
from sqlalchemy import select

from worker.models import ContentItem, SocialAccount
from worker.providers.base import PublishResult
from worker.providers.linkedin import publish_linkedin
from worker.providers.meta import publish_facebook, publish_instagram
from worker.providers.tiktok import publish_tiktok
from worker.providers.youtube import publish_youtube

logger = logging.getLogger("worker.publisher")

# Modo mock: se SOCIAL_PUBLISH_MODE=mock, usa mock (padrao em dev)
PUBLISH_MODE = os.getenv("SOCIAL_PUBLISH_MODE", "mock")


def _decrypt_token(encrypted: str) -> str:
    """Decripta token usando JWT_SECRET_KEY como base Fernet."""
    if not encrypted:
        return ""
    secret = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
    key = hashlib.sha256(secret.encode()).digest()
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.decrypt(encrypted.encode()).decode()


def _get_social_account(session, cost_center_id: str, provider: str) -> SocialAccount | None:
    """Busca conta social conectada para o cost_center e provider."""
    # Mapeia provider_target para provider do SocialAccount
    provider_map = {
        "linkedin": "linkedin",
        "facebook": "meta",
        "instagram": "meta",
        "tiktok": "tiktok",
        "youtube": "youtube",
    }
    sa_provider = provider_map.get(provider, provider)

    stmt = (
        select(SocialAccount)
        .where(
            SocialAccount.cost_center_id == cost_center_id,
            SocialAccount.provider == sa_provider,
            SocialAccount.status == "connected",
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


def publish_content(item: ContentItem, session=None) -> PublishResult:
    """Dispatch para o provider apropriado."""
    if PUBLISH_MODE == "mock" or session is None:
        return _mock_publish(item)

    # Buscar credenciais
    account = _get_social_account(session, item.cost_center_id, item.provider_target)
    if not account:
        return PublishResult(
            success=False,
            error=f"Nenhuma conta {item.provider_target} conectada para este centro de custo. "
                  f"Conecte uma conta em Configuracoes > Redes Sociais.",
        )

    access_token = _decrypt_token(account.token_encrypted)
    if not access_token:
        return PublishResult(
            success=False,
            error=f"Token da conta {item.provider_target} esta vazio ou invalido. Reconecte a conta.",
        )

    # Extrair media URLs do content item
    media_refs = item.media_refs or []
    image_urls = [m.get("url", "") for m in media_refs if m.get("type") == "image" and m.get("url")]
    video_urls = [m.get("url", "") for m in media_refs if m.get("type") == "video" and m.get("url")]
    first_image = image_urls[0] if image_urls else ""
    first_video = video_urls[0] if video_urls else ""

    # Dispatch por provider
    provider = item.provider_target
    account_id = account.account_id

    if provider == "linkedin":
        return publish_linkedin(item.text, access_token, account_id)

    elif provider == "facebook":
        return publish_facebook(item.text, access_token, account_id)

    elif provider == "instagram":
        return publish_instagram(item.text, access_token, account_id, image_url=first_image)

    elif provider == "tiktok":
        return publish_tiktok(
            item.text, access_token,
            video_url=first_video,
            photo_urls=image_urls or None,
        )

    elif provider == "youtube":
        return publish_youtube(item.text, access_token, video_url=first_video)

    else:
        logger.warning("Provider desconhecido: %s, usando mock", provider)
        return _mock_publish(item)


def _mock_publish(item: ContentItem) -> PublishResult:
    """Simula publicacao com delay pequeno."""
    logger.info(
        "Mock publishing content_item=%s to provider=%s",
        item.id,
        item.provider_target,
    )
    time.sleep(0.3)

    return PublishResult(
        success=True,
        provider_post_id=f"mock_{item.id[:8]}",
        provider_post_url=f"https://{item.provider_target}.com/mock/{item.id[:8]}",
    )
