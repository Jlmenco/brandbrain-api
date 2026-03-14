import logging
from sqlmodel import Session, select

from app.models.notification import Notification
from app.models.user import User, OrgMember
from app.models.audit import AuditLog
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

ACTION_TITLES = {
    "submit_review": "Conteudo enviado para revisao",
    "approve": "Conteudo aprovado",
    "request_changes": "Alteracoes solicitadas",
    "reject": "Conteudo rejeitado",
    "schedule": "Conteudo agendado",
    "publish_now": "Conteudo publicado",
}


def _get_admins(db: Session, org_id: str, exclude_user_id: str) -> list[User]:
    """Get admin/owner users of an org, excluding a specific user."""
    stmt = (
        select(User)
        .join(OrgMember, OrgMember.user_id == User.id)
        .where(
            OrgMember.org_id == org_id,
            OrgMember.role.in_(("owner", "admin")),
            User.id != exclude_user_id,
        )
    )
    return list(db.exec(stmt).all())


def _get_submitter(db: Session, content_item_id: str) -> User | None:
    """Find the user who last submitted this content for review (via audit log)."""
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.target_id == content_item_id,
            AuditLog.target_type == "content_item",
            AuditLog.action == "submit_review",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    log = db.exec(stmt).first()
    if log and log.actor_user_id:
        return db.get(User, log.actor_user_id)
    return None


def _get_all_members(db: Session, org_id: str, exclude_user_id: str) -> list[User]:
    """Get all org members except a specific user."""
    stmt = (
        select(User)
        .join(OrgMember, OrgMember.user_id == User.id)
        .where(OrgMember.org_id == org_id, User.id != exclude_user_id)
    )
    return list(db.exec(stmt).all())


def notify_status_change(
    db: Session,
    org_id: str,
    action: str,
    content_item_id: str,
    actor_user_id: str,
    text_preview: str = "",
) -> None:
    """Create in-app notifications + send emails for a content status change."""
    title = ACTION_TITLES.get(action, action)
    body = text_preview[:100] + "..." if len(text_preview) > 100 else text_preview

    # Determine recipients based on action
    if action == "submit_review":
        recipients = _get_admins(db, org_id, actor_user_id)
    elif action in ("approve", "request_changes", "reject"):
        submitter = _get_submitter(db, content_item_id)
        recipients = [submitter] if submitter and submitter.id != actor_user_id else []
    elif action in ("schedule", "publish_now"):
        recipients = _get_all_members(db, org_id, actor_user_id)
    else:
        recipients = []

    for user in recipients:
        notif = Notification(
            org_id=org_id,
            user_id=user.id,
            type="status_change",
            title=title,
            body=body,
            target_type="content_item",
            target_id=content_item_id,
        )
        db.add(notif)

        # Send email
        email_html = (
            f"<h3>{title}</h3>"
            f"<p>{body}</p>"
            f"<p><small>Brand Brain — Notificacao automatica</small></p>"
        )
        send_email(user.email, f"Brand Brain: {title}", email_html)

    if recipients:
        db.commit()
        logger.info(f"Notificacoes criadas: {action} → {len(recipients)} destinatarios")

    # Push notifications para dispositivos mobile
    try:
        from app.services.push_service import send_push_to_users
        sent = send_push_to_users(
            recipients, title, body,
            data={"action": action, "content_item_id": content_item_id},
        )
        if sent:
            logger.info("Push enviado para %d dispositivos", sent)
    except Exception as e:
        logger.warning("Erro ao enviar push notifications: %s", e)

    # Dispatch webhooks reais (Slack, Discord, Teams, Custom)
    try:
        from app.services.webhook_service import dispatch_webhooks
        dispatch_webhooks(db, org_id, action, content_item_id, text_preview)
    except Exception as e:
        logger.warning("Erro ao disparar webhooks: %s", e)
