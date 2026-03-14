"""Admin router — endpoints exclusivos para superadmins (is_superadmin=True)."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.user import User, OrgMember
from app.models.organization import Organization
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Bootstrap — setar primeiro superadmin via secret
# ---------------------------------------------------------------------------

class BootstrapRequest(BaseModel):
    secret: str
    email: str


@router.post("/bootstrap")
def bootstrap_superadmin(body: BootstrapRequest, db: Session = Depends(get_session)):
    """Seta is_superadmin=True para um usuario. Requer BOOTSTRAP_SECRET configurado."""
    if not settings.BOOTSTRAP_SECRET or body.secret != settings.BOOTSTRAP_SECRET:
        raise HTTPException(status_code=403, detail="Secret invalido ou nao configurado")
    user = db.exec(select(User).where(User.email == body.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    user.is_superadmin = True
    db.add(user)
    db.commit()
    return {"detail": f"{user.email} agora e superadmin"}


def require_superadmin(current_user=Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Acesso restrito a superadmins")
    return current_user


# ---------------------------------------------------------------------------
# Listagens
# ---------------------------------------------------------------------------

@router.get("/orgs")
def list_all_orgs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
    _=Depends(require_superadmin),
):
    """Lista todas as organizacoes com contagem de membros."""
    orgs = db.exec(select(Organization).offset(skip).limit(limit)).all()
    total = db.exec(select(func.count()).select_from(Organization)).one()
    result = []
    for org in orgs:
        member_count = db.exec(
            select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org.id)
        ).one()
        result.append({
            "id": org.id,
            "name": org.name,
            "account_type": org.account_type,
            "plan": org.plan,
            "trial_ends_at": org.trial_ends_at,
            "member_count": member_count,
            "created_at": org.created_at,
        })
    return {"total": total, "items": result}


@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
    _=Depends(require_superadmin),
):
    """Lista todos os usuarios."""
    users = db.exec(select(User).offset(skip).limit(limit)).all()
    total = db.exec(select(func.count()).select_from(User)).one()
    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "is_active": u.is_active,
                "is_superadmin": u.is_superadmin,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


# ---------------------------------------------------------------------------
# Acoes manuais
# ---------------------------------------------------------------------------

class AdminActivatePlanRequest(BaseModel):
    plan: str


@router.post("/orgs/{org_id}/activate")
def admin_activate_plan(
    org_id: str,
    body: AdminActivatePlanRequest,
    db: Session = Depends(get_session),
    current_user=Depends(require_superadmin),
):
    """Ativa plano manualmente para qualquer org."""
    from app.models.audit import AuditLog

    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    previous = org.plan
    org.plan = body.plan
    org.trial_ends_at = None
    db.add(org)

    audit = AuditLog(
        org_id=org_id,
        actor_user_id=current_user.id,
        action="admin_activate_plan",
        target_type="organization",
        target_id=org_id,
        metadata_json={"from": previous, "to": body.plan, "by": "superadmin"},
    )
    db.add(audit)
    db.commit()
    return {"detail": "Plano atualizado", "plan": body.plan}


# ---------------------------------------------------------------------------
# Trial reminders (chamado por cron/Lambda diariamente)
# ---------------------------------------------------------------------------

@router.post("/trial-reminders")
def send_trial_reminders(
    db: Session = Depends(get_session),
    _=Depends(require_superadmin),
):
    """Envia emails de aviso de expiracao do trial para D-7 e D-1."""
    from app.services.email_service import send_trial_expiry_email
    from app.config import settings

    now = datetime.utcnow()
    sent = []

    trial_orgs = db.exec(
        select(Organization).where(
            Organization.plan == "trial",
            Organization.trial_ends_at.isnot(None),
        )
    ).all()

    for org in trial_orgs:
        days_left = (org.trial_ends_at - now).days

        if days_left not in (7, 1, 0):
            continue

        # Busca todos os owners da org
        owner_members = db.exec(
            select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.role == "owner")
        ).all()

        for m in owner_members:
            user = db.get(User, m.user_id)
            if not user:
                continue
            upgrade_url = f"{settings.WEB_BASE_URL}/billing"
            send_trial_expiry_email(user.email, user.name, days_left, upgrade_url)
            sent.append({"org": org.name, "email": user.email, "days_left": days_left})

    return {"sent": len(sent), "details": sent}
