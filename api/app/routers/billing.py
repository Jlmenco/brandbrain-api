"""
Router de billing: checkout Asaas + webhook de confirmação de pagamento.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import OrgMember
from app.services import asaas_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_PLANS = asaas_service.VALID_PLANS

# Eventos do Asaas que indicam pagamento confirmado
PAYMENT_CONFIRMED_EVENTS = {
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_APPROVED_BY_RISK_ANALYSIS",
}


@router.get("/plans")
def list_plans():
    """Retorna os planos disponíveis com valores."""
    return [
        {
            "id": plan_id,
            "label": asaas_service.PLAN_LABELS[plan_id],
            "value_brl": asaas_service.PLAN_VALUES[plan_id],
        }
        for plan_id in asaas_service.VALID_PLANS
    ]


@router.post("/checkout")
def create_checkout(
    plan: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """
    Gera link de pagamento Asaas para o upgrade de plano da organização.
    Retorna a URL do checkout.
    """
    if not settings.ASAAS_API_KEY:
        raise HTTPException(status_code=503, detail="Billing não configurado")

    if plan not in VALID_PLANS:
        raise HTTPException(status_code=400, detail=f"Plano inválido: {plan}")

    # Pega a primeira org do usuário (owner/admin)
    member = db.exec(
        select(OrgMember).where(OrgMember.user_id == current_user.id)
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Organização não encontrada")

    org = db.get(Organization, member.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organização não encontrada")

    try:
        url = asaas_service.create_payment_link(org.id, plan)
        if not url:
            raise ValueError("URL vazia retornada pelo Asaas")
        return {"url": url, "plan": plan, "org_id": org.id}
    except Exception as exc:
        logger.error("Erro ao criar link Asaas: %s", exc)
        raise HTTPException(status_code=502, detail="Erro ao gerar link de pagamento")


@router.post("/webhook")
async def asaas_webhook(request: Request, db: Session = Depends(get_session)):
    """
    Webhook do Asaas — recebe notificações de pagamento e atualiza o plano da org.
    URL configurada no painel Asaas: POST /billing/webhook
    """
    # Validar token se configurado (header: asaas-access-token)
    if settings.ASAAS_WEBHOOK_TOKEN:
        token = request.headers.get("asaas-access-token", "")
        if token != settings.ASAAS_WEBHOOK_TOKEN:
            logger.warning("Asaas webhook: token inválido")
            return {"status": "unauthorized"}

    try:
        payload = await request.json()
    except Exception:
        return {"status": "invalid_json"}

    event = payload.get("event", "")
    payment = payload.get("payment", {})

    logger.info("Asaas webhook recebido: event=%s", event)

    if event not in PAYMENT_CONFIRMED_EVENTS:
        return {"status": "ignored", "event": event}

    external_ref = payment.get("externalReference", "")
    if not external_ref or "|" not in external_ref:
        logger.warning("Asaas webhook sem externalReference válido: %s", external_ref)
        return {"status": "no_reference"}

    org_id, plan = external_ref.split("|", 1)

    if plan not in VALID_PLANS:
        logger.warning("Asaas webhook com plano inválido: %s", plan)
        return {"status": "invalid_plan"}

    org = db.get(Organization, org_id)
    if not org:
        logger.warning("Asaas webhook: org %s não encontrada", org_id)
        return {"status": "org_not_found"}

    org.plan = plan
    org.trial_ends_at = None
    db.add(org)
    db.commit()

    logger.info("Plano atualizado: org=%s plan=%s (evento=%s)", org_id, plan, event)
    return {"status": "ok", "org_id": org_id, "plan": plan}
