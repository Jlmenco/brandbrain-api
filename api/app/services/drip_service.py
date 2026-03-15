import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.models.drip import DripCampaign, DripStep, DripEnrollment
from app.models.user import User
from app.services.email_service import send_email, _base_template

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

def enroll_user(
    db: Session,
    campaign_id: str,
    user_id: str,
    org_id: Optional[str] = None,
) -> Optional[DripEnrollment]:
    """Inscreve usuario na campanha se nao estiver ja inscrito (active)."""
    existing = db.exec(
        select(DripEnrollment).where(
            DripEnrollment.campaign_id == campaign_id,
            DripEnrollment.user_id == user_id,
            DripEnrollment.status == "active",
        )
    ).first()
    if existing:
        logger.debug("User %s already enrolled in campaign %s", user_id, campaign_id)
        return None

    # Buscar primeiro step para calcular next_send_at
    first_step = db.exec(
        select(DripStep)
        .where(DripStep.campaign_id == campaign_id)
        .order_by(DripStep.step_order.asc())
    ).first()
    if not first_step:
        logger.warning("Campaign %s has no steps, skipping enrollment", campaign_id)
        return None

    now = datetime.utcnow()
    enrollment = DripEnrollment(
        campaign_id=campaign_id,
        user_id=user_id,
        org_id=org_id,
        current_step=0,
        next_send_at=now + timedelta(hours=first_step.delay_hours),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    logger.info("Enrolled user %s in campaign %s, next_send_at=%s", user_id, campaign_id, enrollment.next_send_at)
    return enrollment


def cancel_enrollment(db: Session, enrollment_id: str) -> bool:
    """Cancela enrollment. Retorna True se encontrado e cancelado."""
    enrollment = db.get(DripEnrollment, enrollment_id)
    if not enrollment or enrollment.status != "active":
        return False
    enrollment.status = "cancelled"
    db.add(enrollment)
    db.commit()
    logger.info("Cancelled enrollment %s", enrollment_id)
    return True


def auto_enroll_on_event(
    db: Session,
    event: str,
    user_id: str,
    org_id: Optional[str] = None,
) -> int:
    """Busca campanhas ativas com trigger_event=event e inscreve o usuario.
    Campanhas globais (org_id=None) se aplicam a todos.
    Retorna quantidade de enrollments criados."""
    campaigns = db.exec(
        select(DripCampaign).where(
            DripCampaign.trigger_event == event,
            DripCampaign.is_active == True,  # noqa: E712
        )
    ).all()

    count = 0
    for campaign in campaigns:
        # Campanha global ou da mesma org
        if campaign.org_id is not None and campaign.org_id != org_id:
            continue
        result = enroll_user(db, campaign.id, user_id, org_id)
        if result:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Processing (chamado pelo worker)
# ---------------------------------------------------------------------------

def process_pending_drips(db: Session) -> int:
    """Processa enrollments com next_send_at <= now. Retorna quantidade processada."""
    now = datetime.utcnow()
    enrollments = db.exec(
        select(DripEnrollment).where(
            DripEnrollment.status == "active",
            DripEnrollment.next_send_at != None,  # noqa: E711
            DripEnrollment.next_send_at <= now,
        )
    ).all()

    processed = 0
    for enrollment in enrollments:
        try:
            _send_step(db, enrollment)
            processed += 1
        except Exception:
            logger.exception("Error processing enrollment %s", enrollment.id)
    return processed


def _send_step(db: Session, enrollment: DripEnrollment) -> None:
    """Envia o step atual e avanca o enrollment."""
    # Buscar steps da campanha ordenados
    steps = db.exec(
        select(DripStep)
        .where(DripStep.campaign_id == enrollment.campaign_id)
        .order_by(DripStep.step_order.asc())
    ).all()

    if enrollment.current_step >= len(steps):
        # Todos os steps enviados
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
        enrollment.next_send_at = None
        db.add(enrollment)
        db.commit()
        logger.info("Enrollment %s completed (all steps sent)", enrollment.id)
        return

    step = steps[enrollment.current_step]
    user = db.get(User, enrollment.user_id)
    if not user:
        logger.warning("User %s not found for enrollment %s, cancelling", enrollment.user_id, enrollment.id)
        enrollment.status = "cancelled"
        db.add(enrollment)
        db.commit()
        return

    # Renderizar template
    org_name = ""
    if enrollment.org_id:
        from app.models.organization import Organization
        org = db.get(Organization, enrollment.org_id)
        if org:
            org_name = org.name or ""

    body_content = step.body_template.format(
        name=user.name or user.email,
        org_name=org_name,
        email=user.email,
        upgrade_url=f"https://app.brandbrain.com.br/billing",
    )
    html = _base_template(body_content)
    subject = step.subject.format(
        name=user.name or user.email,
        org_name=org_name,
    )

    send_email(user.email, subject, html)
    logger.info("Sent drip step %d to %s (campaign=%s)", enrollment.current_step, user.email, enrollment.campaign_id)

    # Avancar para proximo step
    enrollment.current_step += 1

    if enrollment.current_step >= len(steps):
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
        enrollment.next_send_at = None
    else:
        next_step = steps[enrollment.current_step]
        enrollment.next_send_at = datetime.utcnow() + timedelta(hours=next_step.delay_hours)

    db.add(enrollment)
    db.commit()
