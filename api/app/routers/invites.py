"""Endpoints publicos para aceitar convites de membros."""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.invite import OrgInvite
from app.models.organization import Organization
from app.models.user import User, OrgMember
from app.services.email_service import send_invite_email
from app.services.auth_service import hash_password, create_access_token
from app.config import settings

router = APIRouter()


class InviteInfoResponse(BaseModel):
    org_name: str
    email: str
    role: str
    inviter_name: str
    expired: bool


class AcceptInviteRequest(BaseModel):
    name: str | None = None       # se novo usuario
    password: str | None = None   # se novo usuario


@router.get("/{token}", response_model=InviteInfoResponse)
def get_invite(token: str, db: Session = Depends(get_session)):
    """Retorna info do convite para exibir na tela de aceite."""
    invite = db.exec(select(OrgInvite).where(OrgInvite.token == token)).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite nao encontrado")

    org = db.get(Organization, invite.org_id)
    inviter = db.get(User, invite.invited_by)

    return InviteInfoResponse(
        org_name=org.name if org else "Organizacao",
        email=invite.email,
        role=invite.role,
        inviter_name=inviter.name if inviter else "Alguem",
        expired=invite.expires_at < datetime.utcnow() or invite.accepted_at is not None,
    )


@router.post("/{token}/accept")
def accept_invite(token: str, body: AcceptInviteRequest, db: Session = Depends(get_session)):
    """Aceita um convite. Se o email ja existe como usuario, faz login e adiciona a org.
    Se nao existe, cria o usuario com name+password e adiciona."""
    invite = db.exec(select(OrgInvite).where(OrgInvite.token == token)).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite nao encontrado")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Convite ja foi aceito")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Convite expirado")

    # Busca ou cria o usuario pelo email do convite
    user = db.exec(select(User).where(User.email == invite.email)).first()
    if not user:
        if not body.name or not body.password:
            raise HTTPException(status_code=400, detail="Nome e senha obrigatorios para novo usuario")
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")
        user = User(
            email=invite.email,
            name=body.name,
            hashed_password=hash_password(body.password),
        )
        db.add(user)
        db.flush()

    # Verifica se ja e membro
    existing_member = db.exec(
        select(OrgMember).where(OrgMember.org_id == invite.org_id, OrgMember.user_id == user.id)
    ).first()
    if not existing_member:
        member = OrgMember(org_id=invite.org_id, user_id=user.id, role=invite.role)
        db.add(member)

    invite.accepted_at = datetime.utcnow()
    db.add(invite)
    db.commit()

    jwt_token = create_access_token({"sub": user.id, "email": user.email})
    return {"access_token": jwt_token, "token_type": "bearer"}
