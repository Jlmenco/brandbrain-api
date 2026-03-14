"""
Serviço de integração com o Asaas (gateway de pagamento brasileiro).
Docs: https://docs.asaas.com/reference
"""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

ASAAS_BASE = (
    "https://sandbox.asaas.com/api/v3"
    if settings.ASAAS_SANDBOX
    else "https://www.asaas.com/api/v3"
)

# Planos e valores mensais (BRL)
PLAN_VALUES: dict[str, float] = {
    "solo_monthly": 297.00,
    "agency_monthly": 697.00,
    "group_monthly": 1497.00,
}

PLAN_LABELS: dict[str, str] = {
    "solo_monthly": "Brand Brain Solo – Mensal",
    "agency_monthly": "Brand Brain Agência – Mensal",
    "group_monthly": "Brand Brain Grupo – Mensal",
}

VALID_PLANS = set(PLAN_VALUES.keys())


def _headers() -> dict:
    return {
        "access_token": settings.ASAAS_API_KEY,
        "Content-Type": "application/json",
    }


def create_customer(name: str, email: str) -> str:
    """
    Cria (ou recupera) cliente no Asaas. Retorna o Asaas customer ID.
    Em caso de erro, loga e levanta exceção.
    """
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{ASAAS_BASE}/customers",
            json={"name": name, "email": email, "notificationDisabled": False},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Asaas customer criado: %s", data.get("id"))
        return data["id"]


def get_or_create_customer(name: str, email: str) -> str:
    """
    Verifica se cliente já existe pelo email; se não, cria.
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{ASAAS_BASE}/customers",
            params={"email": email},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        existing = data.get("data", [])
        if existing:
            return existing[0]["id"]
        return create_customer(name, email)


def create_payment_link(org_id: str, plan: str) -> str:
    """
    Cria link de pagamento recorrente no Asaas para o plano especificado.
    Retorna a URL do checkout.
    """
    if plan not in VALID_PLANS:
        raise ValueError(f"Plano inválido: {plan}")

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{ASAAS_BASE}/paymentLinks",
            json={
                "name": PLAN_LABELS[plan],
                "billingType": "UNDEFINED",
                "chargeType": "RECURRENT",
                "value": PLAN_VALUES[plan],
                "subscriptionCycle": "MONTHLY",
                "externalReference": f"{org_id}|{plan}",
                "notificationEnabled": True,
            },
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        url = data.get("url") or data.get("viewLink") or ""
        logger.info("Asaas payment link criado para org %s plano %s: %s", org_id, plan, url)
        return url
