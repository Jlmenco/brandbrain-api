import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.services.email_service import send_reset_password_email
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_session)):
    from app.models.organization import Organization
    from app.models.user import OrgMember

    existing = db.exec(select(User).where(User.email == body.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.flush()

    org = Organization(
        name=body.org_name,
        plan="trial",
        trial_ends_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(org)
    db.flush()

    member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
    db.add(member)
    db.commit()

    # Auto-enroll em campanhas drip de boas-vindas
    try:
        from app.services.drip_service import auto_enroll_on_event
        auto_enroll_on_event(db, "welcome", user.id, org.id)
    except Exception:
        pass  # Nao deve bloquear registro

    # Auto-complete onboarding profile_setup
    try:
        from app.services.onboarding_service import complete_step
        complete_step(db, user.id, org.id, "profile_setup")
    except Exception:
        pass

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.email == body.email)).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout():
    return {"detail": "Logged out (client should discard token)"}


@router.get("/me", response_model=UserResponse)
def me(current_user=Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Forgot / Reset password
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.get("/check-email")
def check_email(email: str, db: Session = Depends(get_session)):
    """Verifica se um email ja esta cadastrado (usado no fluxo de convite)."""
    exists = db.exec(select(User).where(User.email == email)).first() is not None
    return {"exists": exists}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_session)):
    """Gera token de reset e envia email. Sempre retorna 200 para nao revelar emails."""
    user = db.exec(select(User).where(User.email == body.email)).first()
    if user:
        token_value = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_value,
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        db.add(reset_token)
        db.commit()

        reset_url = f"{settings.WEB_BASE_URL}/redefinir-senha?token={token_value}"
        send_reset_password_email(user.email, user.name, reset_url)

    return {"detail": "Se o email estiver cadastrado, voce recebera um link em breve."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_session)):
    """Valida token e redefine a senha."""
    reset_token = db.exec(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    ).first()

    if not reset_token or reset_token.used or reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")

    user = db.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    user.hashed_password = hash_password(body.new_password)
    reset_token.used = True
    db.add(user)
    db.add(reset_token)
    db.commit()

    return {"detail": "Senha redefinida com sucesso"}
