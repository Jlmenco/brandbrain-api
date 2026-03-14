import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.webhook import WebhookConfig
from app.dependencies import get_current_user, check_role, ADMIN_ROLES

logger = logging.getLogger("app.webhooks")

router = APIRouter()


class WebhookCreate(BaseModel):
    name: str
    provider: str   # slack | discord | teams | custom
    url: str
    events: list = []  # [] = todos os eventos


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: str
    org_id: str
    name: str
    provider: str
    url: str
    events: list
    is_active: bool
    created_at: datetime


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(
    org_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return db.exec(
        select(WebhookConfig).where(WebhookConfig.org_id == org_id)
        .order_by(WebhookConfig.created_at.desc())
    ).all()


@router.post("", response_model=WebhookResponse)
def create_webhook(
    body: WebhookCreate,
    org_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    hook = WebhookConfig(org_id=org_id, created_by=current_user.id, **body.model_dump())
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return hook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    hook = db.get(WebhookConfig, webhook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    check_role(db, current_user.id, hook.org_id, ADMIN_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(hook, key, val)
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return hook


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    hook = db.get(WebhookConfig, webhook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    check_role(db, current_user.id, hook.org_id, ADMIN_ROLES)
    db.delete(hook)
    db.commit()


@router.post("/{webhook_id}/test", status_code=200)
def test_webhook(
    webhook_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Dispara uma mensagem de teste no webhook."""
    hook = db.get(WebhookConfig, webhook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    check_role(db, current_user.id, hook.org_id, ADMIN_ROLES)

    from app.services.webhook_service import _dispatch_one
    try:
        _dispatch_one(hook, "🔔 Teste de Webhook", "Este é um teste de conexão do Brand Brain.", "test-000")
        return {"status": "ok", "message": "Webhook disparado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao disparar webhook: {e}")
