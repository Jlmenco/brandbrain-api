from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user, check_role, ADMIN_ROLES
from app.models.drip import DripCampaign, DripStep, DripEnrollment
from app.services.drip_service import enroll_user, cancel_enrollment

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DripStepInput(BaseModel):
    step_order: int
    delay_hours: int = 0
    subject: str
    body_template: str


class DripCampaignCreate(BaseModel):
    name: str
    trigger_event: str  # welcome | trial_expiring | inactive | custom
    org_id: Optional[str] = None
    steps: list[DripStepInput] = []


class DripCampaignUpdate(BaseModel):
    name: Optional[str] = None
    trigger_event: Optional[str] = None
    is_active: Optional[bool] = None
    steps: Optional[list[DripStepInput]] = None


class DripStepResponse(BaseModel):
    id: str
    step_order: int
    delay_hours: int
    subject: str
    body_template: str


class DripCampaignResponse(BaseModel):
    id: str
    org_id: Optional[str]
    name: str
    trigger_event: str
    is_active: bool
    created_at: datetime
    steps: list[DripStepResponse] = []


class DripEnrollmentResponse(BaseModel):
    id: str
    campaign_id: str
    user_id: str
    org_id: Optional[str]
    current_step: int
    status: str
    enrolled_at: datetime
    next_send_at: Optional[datetime]
    completed_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _campaign_response(campaign: DripCampaign, steps: list[DripStep]) -> DripCampaignResponse:
    return DripCampaignResponse(
        id=campaign.id,
        org_id=campaign.org_id,
        name=campaign.name,
        trigger_event=campaign.trigger_event,
        is_active=campaign.is_active,
        created_at=campaign.created_at,
        steps=[
            DripStepResponse(
                id=s.id,
                step_order=s.step_order,
                delay_hours=s.delay_hours,
                subject=s.subject,
                body_template=s.body_template,
            )
            for s in sorted(steps, key=lambda s: s.step_order)
        ],
    )


# ---------------------------------------------------------------------------
# CRUD Campanhas
# ---------------------------------------------------------------------------

@router.get("", response_model=list[DripCampaignResponse])
def list_campaigns(
    org_id: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Lista campanhas drip. Admin pode ver de qualquer org."""
    stmt = select(DripCampaign)
    if org_id:
        check_role(db, current_user.id, org_id, ADMIN_ROLES)
        stmt = stmt.where(
            (DripCampaign.org_id == org_id) | (DripCampaign.org_id == None)  # noqa: E711
        )
    elif not current_user.is_superadmin:
        raise HTTPException(status_code=400, detail="org_id e obrigatorio")

    campaigns = db.exec(stmt.order_by(DripCampaign.created_at.desc())).all()
    result = []
    for c in campaigns:
        steps = db.exec(
            select(DripStep).where(DripStep.campaign_id == c.id)
        ).all()
        result.append(_campaign_response(c, steps))
    return result


@router.post("", response_model=DripCampaignResponse)
def create_campaign(
    body: DripCampaignCreate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Cria campanha drip com steps. Requer admin da org ou superadmin."""
    if body.org_id:
        check_role(db, current_user.id, body.org_id, ADMIN_ROLES)
    elif not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Apenas superadmin pode criar campanhas globais")

    campaign = DripCampaign(
        name=body.name,
        trigger_event=body.trigger_event,
        org_id=body.org_id,
    )
    db.add(campaign)
    db.flush()

    steps = []
    for s in body.steps:
        step = DripStep(
            campaign_id=campaign.id,
            step_order=s.step_order,
            delay_hours=s.delay_hours,
            subject=s.subject,
            body_template=s.body_template,
        )
        db.add(step)
        steps.append(step)

    db.commit()
    db.refresh(campaign)
    return _campaign_response(campaign, steps)


@router.patch("/{campaign_id}", response_model=DripCampaignResponse)
def update_campaign(
    campaign_id: str,
    body: DripCampaignUpdate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Atualiza campanha drip. Se steps forem fornecidos, substitui todos."""
    campaign = db.get(DripCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    if campaign.org_id:
        check_role(db, current_user.id, campaign.org_id, ADMIN_ROLES)
    elif not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissao")

    if body.name is not None:
        campaign.name = body.name
    if body.trigger_event is not None:
        campaign.trigger_event = body.trigger_event
    if body.is_active is not None:
        campaign.is_active = body.is_active

    campaign.updated_at = datetime.utcnow()
    db.add(campaign)

    # Se steps fornecidos, substituir todos
    if body.steps is not None:
        old_steps = db.exec(
            select(DripStep).where(DripStep.campaign_id == campaign_id)
        ).all()
        for s in old_steps:
            db.delete(s)

        new_steps = []
        for s in body.steps:
            step = DripStep(
                campaign_id=campaign_id,
                step_order=s.step_order,
                delay_hours=s.delay_hours,
                subject=s.subject,
                body_template=s.body_template,
            )
            db.add(step)
            new_steps.append(step)
        db.commit()
        db.refresh(campaign)
        return _campaign_response(campaign, new_steps)

    db.commit()
    db.refresh(campaign)
    steps = db.exec(select(DripStep).where(DripStep.campaign_id == campaign_id)).all()
    return _campaign_response(campaign, steps)


@router.delete("/{campaign_id}")
def deactivate_campaign(
    campaign_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Desativa campanha (soft delete)."""
    campaign = db.get(DripCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    if campaign.org_id:
        check_role(db, current_user.id, campaign.org_id, ADMIN_ROLES)
    elif not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissao")

    campaign.is_active = False
    campaign.updated_at = datetime.utcnow()
    db.add(campaign)
    db.commit()
    return {"detail": "Campanha desativada"}


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

@router.get("/{campaign_id}/enrollments", response_model=list[DripEnrollmentResponse])
def list_enrollments(
    campaign_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Lista enrollments de uma campanha."""
    campaign = db.get(DripCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    if campaign.org_id:
        check_role(db, current_user.id, campaign.org_id, ADMIN_ROLES)
    elif not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissao")

    stmt = select(DripEnrollment).where(DripEnrollment.campaign_id == campaign_id)
    if status:
        stmt = stmt.where(DripEnrollment.status == status)

    enrollments = db.exec(stmt.order_by(DripEnrollment.enrolled_at.desc())).all()
    return enrollments


@router.post("/{campaign_id}/enrollments/{enrollment_id}/cancel")
def cancel_enrollment_endpoint(
    campaign_id: str,
    enrollment_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Cancela um enrollment."""
    campaign = db.get(DripCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    if campaign.org_id:
        check_role(db, current_user.id, campaign.org_id, ADMIN_ROLES)
    elif not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissao")

    success = cancel_enrollment(db, enrollment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Enrollment nao encontrado ou ja cancelado")

    return {"detail": "Enrollment cancelado"}
