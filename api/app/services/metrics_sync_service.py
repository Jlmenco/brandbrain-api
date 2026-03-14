"""
Sync de métricas reais das APIs sociais.
Busca impressões, likes, comentários, shares de posts publicados.
"""
import base64
import hashlib
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from app.models.content import ContentItem
from app.models.metrics import MetricsDaily
from app.models.social import SocialAccount

logger = logging.getLogger("app.metrics_sync")


def _decrypt_token(encrypted: str) -> str:
    if not encrypted:
        return ""
    secret = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
    key = hashlib.sha256(secret.encode()).digest()
    f = Fernet(base64.urlsafe_b64encode(key))
    try:
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return ""


def _get_token(db: Session, cost_center_id: str, provider_key: str) -> Optional[str]:
    """Busca token de acesso para o cost center + provider."""
    provider_map = {"linkedin": "linkedin", "facebook": "meta", "instagram": "meta",
                    "tiktok": "tiktok", "youtube": "youtube"}
    sa_provider = provider_map.get(provider_key, provider_key)
    acct = db.exec(
        select(SocialAccount).where(
            SocialAccount.cost_center_id == cost_center_id,
            SocialAccount.provider == sa_provider,
            SocialAccount.status == "connected",
        )
    ).first()
    if not acct:
        return None
    return _decrypt_token(acct.token_encrypted) or None


def sync_metrics_for_content(db: Session, content_item_id: str, sync_date: Optional[date] = None) -> dict:
    """Sincroniza métricas de um content item publicado.

    Returns dict com totais obtidos.
    """
    ci = db.get(ContentItem, content_item_id)
    if not ci or ci.status != "posted" or not ci.provider_post_id:
        return {"skipped": True, "reason": "not posted or no provider_post_id"}

    target_date = sync_date or date.today()
    token = _get_token(db, ci.cost_center_id, ci.provider_target)
    if not token:
        return {"skipped": True, "reason": "no token"}

    try:
        metrics = _fetch_metrics(ci.provider_target, ci.provider_post_id, token)
    except Exception as e:
        logger.warning("Falha ao buscar métricas %s/%s: %s", ci.provider_target, ci.provider_post_id, e)
        return {"error": str(e)}

    # Upsert MetricsDaily
    existing = db.exec(
        select(MetricsDaily).where(
            MetricsDaily.content_item_id == content_item_id,
            MetricsDaily.date == target_date,
        )
    ).first()

    if existing:
        for k, v in metrics.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        db.add(existing)
    else:
        record = MetricsDaily(
            content_item_id=content_item_id,
            date=target_date,
            **metrics,
        )
        db.add(record)

    db.commit()
    logger.info("Métricas sincronizadas: content=%s date=%s %s", content_item_id, target_date, metrics)
    return metrics


def _fetch_metrics(provider: str, post_id: str, token: str) -> dict:
    """Busca métricas da API do provider."""
    if provider == "linkedin":
        return _fetch_linkedin(post_id, token)
    elif provider == "facebook":
        return _fetch_facebook(post_id, token)
    elif provider == "instagram":
        return _fetch_instagram(post_id, token)
    elif provider == "youtube":
        return _fetch_youtube(post_id, token)
    else:
        return {}


def _fetch_linkedin(post_id: str, token: str) -> dict:
    url = f"https://api.linkedin.com/rest/socialActions/{post_id}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers={
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": "202401",
        })
        if not resp.is_success:
            return {}
        data = resp.json()
    return {
        "likes": data.get("likesSummary", {}).get("totalLikes", 0),
        "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
        "shares": data.get("shareStatistics", {}).get("totalShareStatistics", {}).get("shareCount", 0),
        "impressions": data.get("shareStatistics", {}).get("totalShareStatistics", {}).get("impressionCount", 0),
        "clicks": data.get("shareStatistics", {}).get("totalShareStatistics", {}).get("clickCount", 0),
    }


def _fetch_facebook(post_id: str, token: str) -> dict:
    url = f"https://graph.facebook.com/v21.0/{post_id}/insights"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, params={
            "metric": "post_impressions,post_engaged_users,post_reactions_like_total,post_clicks",
            "access_token": token,
        })
        if not resp.is_success:
            return {}
        data = resp.json().get("data", [])
    metrics = {}
    for item in data:
        name = item.get("name", "")
        val = item.get("values", [{}])[-1].get("value", 0)
        if name == "post_impressions": metrics["impressions"] = val
        elif name == "post_reactions_like_total": metrics["likes"] = val
        elif name == "post_clicks": metrics["clicks"] = val
    return metrics


def _fetch_instagram(post_id: str, token: str) -> dict:
    url = f"https://graph.facebook.com/v21.0/{post_id}/insights"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, params={
            "metric": "impressions,reach,likes,comments,shares",
            "access_token": token,
        })
        if not resp.is_success:
            return {}
        data = resp.json().get("data", [])
    metrics = {}
    for item in data:
        name = item.get("name", "")
        val = item.get("values", [{}])[-1].get("value", 0) if item.get("values") else item.get("id", 0)
        if name == "impressions": metrics["impressions"] = val
        elif name == "likes": metrics["likes"] = val
        elif name == "comments": metrics["comments"] = val
        elif name == "shares": metrics["shares"] = val
    return metrics


def _fetch_youtube(video_id: str, token: str) -> dict:
    url = "https://www.googleapis.com/youtube/v3/videos"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, params={
            "id": video_id,
            "part": "statistics",
            "access_token": token,
        })
        if not resp.is_success:
            return {}
        items = resp.json().get("items", [])
    if not items:
        return {}
    stats = items[0].get("statistics", {})
    return {
        "impressions": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
    }
