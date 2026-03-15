from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.organization import Organization
from app.models.user import OrgMember
from app.schemas.organization import (
    OrgCreate, OrgResponse, OrgUpdate, OrgMemberCreate, OrgMemberResponse,
    SoloSetupRequest, OrgUpgradeRequest, OrgActivateRequest,
)
from app.dependencies import get_current_user, check_role, ADMIN_ROLES

router = APIRouter()


def _org_response(org: Organization, role: str | None = None) -> OrgResponse:
    return OrgResponse(
        id=org.id,
        name=org.name,
        role=role,
        billing_alert_threshold=org.billing_alert_threshold,
        account_type=org.account_type,
        parent_org_id=org.parent_org_id,
        plan=org.plan,
        trial_ends_at=org.trial_ends_at,
    )


@router.get("", response_model=list[OrgResponse])
def list_orgs(db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    memberships = db.exec(select(OrgMember).where(OrgMember.user_id == current_user.id)).all()
    if not memberships:
        return []
    org_ids = [m.org_id for m in memberships]
    role_map = {m.org_id: m.role for m in memberships}
    orgs = db.exec(select(Organization).where(Organization.id.in_(org_ids))).all()
    return [_org_response(org, role_map.get(org.id)) for org in orgs]


@router.post("", response_model=OrgResponse)
def create_org(body: OrgCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org = Organization(name=body.name, account_type=body.account_type)
    db.add(org)
    db.flush()
    member = OrgMember(org_id=org.id, user_id=current_user.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(org)
    return _org_response(org, "owner")


@router.get("/{org_id}", response_model=OrgResponse)
def get_org(org_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    member = db.exec(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == current_user.id)
    ).first()
    return _org_response(org, member.role if member else None)


@router.patch("/{org_id}", response_model=OrgResponse)
def update_org(
    org_id: str,
    body: OrgUpdate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Atualiza configuracoes da organizacao. Requer admin."""
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if body.name is not None:
        org.name = body.name
    if body.billing_alert_threshold is not None:
        org.billing_alert_threshold = body.billing_alert_threshold
    if body.account_type is not None:
        org.account_type = body.account_type
    db.add(org)
    db.commit()
    db.refresh(org)
    member = db.exec(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == current_user.id)
    ).first()
    return _org_response(org, member.role if member else None)


@router.post("/{org_id}/setup-solo", response_model=OrgResponse)
def setup_solo(
    org_id: str,
    body: SoloSetupRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Setup automatico do perfil Solo: cria CostCenter + Influencer em uma unica transacao."""
    from app.models.cost_center import CostCenter
    from app.models.influencer import Influencer

    check_role(db, current_user.id, org_id, ("owner",))
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.account_type != "solo":
        raise HTTPException(status_code=400, detail="Esta operacao e exclusiva do perfil Solo.")

    # Criar CostCenter automatico
    cc = CostCenter(
        name=body.brand_name,
        code="SOLO",
        org_id=org_id,
        created_by=current_user.id,
    )
    db.add(cc)
    db.flush()

    # Criar Influencer automatico (representa a propria marca do usuario)
    influencer = Influencer(
        org_id=org_id,
        name=body.brand_name,
        niche=body.niche,
        type="master",
        created_by=current_user.id,
    )
    db.add(influencer)
    db.commit()
    db.refresh(org)
    return _org_response(org, "owner")


@router.post("/{org_id}/upgrade", response_model=OrgResponse)
def upgrade_org(
    org_id: str,
    body: OrgUpgradeRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Faz upgrade do perfil Solo para Agency."""
    from app.models.audit import AuditLog

    check_role(db, current_user.id, org_id, ("owner",))
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.account_type == body.target_type:
        raise HTTPException(status_code=400, detail="Organizacao ja esta neste perfil.")

    previous = org.account_type
    org.account_type = body.target_type
    db.add(org)

    audit = AuditLog(
        org_id=org_id,
        actor_user_id=current_user.id,
        action="upgrade_plan",
        target_type="organization",
        target_id=org_id,
        metadata_json={"from": previous, "to": body.target_type},
    )
    db.add(audit)
    db.commit()
    db.refresh(org)
    return _org_response(org, "owner")


@router.get("/{org_id}/group-summary")
def group_summary(org_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    """Retorna metricas consolidadas das filiais de um grupo."""
    from app.models.cost_center import CostCenter
    from app.models.content import ContentItem
    from app.models.tracking import Lead

    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.account_type != "group":
        raise HTTPException(status_code=400, detail="Esta operacao e exclusiva do perfil Group.")

    # Filiais: orgs com parent_org_id == org_id
    filiais = db.exec(select(Organization).where(Organization.parent_org_id == org_id)).all()
    filial_ids = [f.id for f in filiais]

    summary = []
    for filial in filiais:
        # Cost centers dessa filial
        ccs = db.exec(select(CostCenter).where(CostCenter.org_id == filial.id)).all()
        cc_ids = [cc.id for cc in ccs]

        total_content = 0
        posted_content = 0
        total_leads = 0

        if cc_ids:
            total_content = db.exec(
                select(ContentItem).where(ContentItem.cost_center_id.in_(cc_ids))
            ).all().__len__()
            posted_content = db.exec(
                select(ContentItem).where(
                    ContentItem.cost_center_id.in_(cc_ids),
                    ContentItem.status == "posted"
                )
            ).all().__len__()
            total_leads = db.exec(
                select(Lead).where(Lead.cost_center_id.in_(cc_ids))
            ).all().__len__()

        summary.append({
            "org_id": filial.id,
            "name": filial.name,
            "total_content": total_content,
            "posted_content": posted_content,
            "total_leads": total_leads,
        })

    return {
        "group_id": org_id,
        "group_name": org.name,
        "total_filiais": len(filiais),
        "filiais": summary,
    }


@router.post("/{org_id}/filiais", response_model=OrgResponse)
def create_filial(
    org_id: str,
    body: OrgCreate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Cria uma filial (sub-org) vinculada a um grupo."""
    check_role(db, current_user.id, org_id, ("owner",))
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.account_type != "group":
        raise HTTPException(status_code=400, detail="Esta operacao e exclusiva do perfil Group.")

    filial = Organization(name=body.name, account_type="agency", parent_org_id=org_id)
    db.add(filial)
    db.flush()
    member = OrgMember(org_id=filial.id, user_id=current_user.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(filial)
    return _org_response(filial, "owner")


@router.post("/{org_id}/activate", response_model=OrgResponse)
def activate_plan(
    org_id: str,
    body: OrgActivateRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Ativa um plano pago (encerra trial). Requer owner."""
    from app.models.audit import AuditLog

    check_role(db, current_user.id, org_id, ("owner",))
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    previous_plan = org.plan
    org.plan = body.plan
    org.trial_ends_at = None  # encerra o trial
    db.add(org)

    audit = AuditLog(
        org_id=org_id,
        actor_user_id=current_user.id,
        action="activate_plan",
        target_type="organization",
        target_id=org_id,
        metadata_json={"from": previous_plan, "to": body.plan},
    )
    db.add(audit)
    db.commit()
    db.refresh(org)
    return _org_response(org, "owner")


@router.post("/{org_id}/invite")
def invite_member(
    org_id: str,
    body: OrgMemberCreate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Convida um membro por email. Requer admin."""
    import secrets
    from datetime import timedelta
    from app.models.invite import OrgInvite
    from app.services.email_service import send_invite_email

    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    token_value = secrets.token_urlsafe(32)
    invite = OrgInvite(
        org_id=org_id,
        invited_by=current_user.id,
        email=body.user_id,  # user_id field reutilizado como email no convite
        role=body.role,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()

    from app.config import settings
    invite_url = f"{settings.WEB_BASE_URL}/aceitar-convite?token={token_value}"
    send_invite_email(body.user_id, org.name, current_user.name, body.role, invite_url)

    return {"detail": "Convite enviado", "email": body.user_id}


@router.post("/{org_id}/members", response_model=OrgMemberResponse)
def add_member(org_id: str, body: OrgMemberCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    member = OrgMember(org_id=org_id, user_id=body.user_id, role=body.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
