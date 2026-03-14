"""Webhook dispatch service — envia notificacoes para Slack, Discord, Teams, e custom URLs."""
import logging
import httpx
from sqlmodel import Session, select

from app.models.webhook import WebhookConfig

logger = logging.getLogger(__name__)

ACTION_LABELS = {
    "submit_review": "📋 Conteúdo enviado para revisão",
    "approve": "✅ Conteúdo aprovado",
    "request_changes": "✏️ Alterações solicitadas",
    "reject": "❌ Conteúdo rejeitado",
    "schedule": "📅 Conteúdo agendado",
    "publish_now": "🚀 Conteúdo publicado",
}


def dispatch_webhooks(
    db: Session,
    org_id: str,
    action: str,
    content_item_id: str,
    text_preview: str = "",
) -> None:
    """Busca webhooks ativos para o org e dispara para os que estão inscritos no action."""
    hooks = db.exec(
        select(WebhookConfig).where(
            WebhookConfig.org_id == org_id,
            WebhookConfig.is_active == True,  # noqa: E712
        )
    ).all()

    relevant = [h for h in hooks if not h.events or action in h.events]
    if not relevant:
        return

    label = ACTION_LABELS.get(action, action)
    preview = text_preview[:120] + "..." if len(text_preview) > 120 else text_preview

    for hook in relevant:
        try:
            _dispatch_one(hook, label, preview, content_item_id)
        except Exception as e:
            logger.warning("Webhook %s falhou: %s", hook.id, e)


def _dispatch_one(hook: WebhookConfig, label: str, preview: str, content_item_id: str) -> None:
    if hook.provider == "slack":
        payload = {
            "text": f"*Brand Brain* — {label}",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{label}*\n{preview}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Content ID: `{content_item_id}`"}]},
            ],
        }
    elif hook.provider == "discord":
        payload = {
            "embeds": [{
                "title": "Brand Brain",
                "description": f"**{label}**\n{preview}",
                "color": 0x6366F1,
                "footer": {"text": f"Content: {content_item_id[:8]}"},
            }]
        }
    elif hook.provider == "teams":
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": label,
            "themeColor": "6366F1",
            "title": "Brand Brain",
            "sections": [{"text": f"**{label}**\n\n{preview}"}],
        }
    else:
        # Custom: POST genérico com JSON simples
        payload = {
            "event": label,
            "content_item_id": content_item_id,
            "preview": preview,
        }

    with httpx.Client(timeout=10) as client:
        resp = client.post(hook.url, json=payload)
        resp.raise_for_status()
    logger.info("Webhook %s (%s) disparado: %s", hook.name, hook.provider, label)
