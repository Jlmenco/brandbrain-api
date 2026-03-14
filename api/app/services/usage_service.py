"""Tracking de uso de recursos de IA e publicacao por org/cost_center."""
import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.usage import UsageLog

logger = logging.getLogger("app.usage")

# Limites mensais por plano (None = ilimitado)
PLAN_QUOTAS: dict[str, dict[str, int | None]] = {
    "trial":          {"video": 2,   "avatar": 3},
    "solo_monthly":   {"video": 10,  "avatar": 10},
    "agency_monthly": {"video": 50,  "avatar": 30},
    "group_monthly":  {"video": 200, "avatar": None},
}
# Plano desconhecido/active herda o maior
_DEFAULT_QUOTA: dict[str, int | None] = {"video": 200, "avatar": None}

# Preços estimados por unidade (USD)
UNIT_COSTS = {
    "openai_tokens": 0.00000015,       # gpt-4o-mini input: $0.15/1M tokens
    "anthropic_tokens": 0.00000025,    # claude-haiku: $0.25/1M tokens
    "elevenlabs_chars": 0.000030,      # ~$30/1M chars
    "hedra_seconds": 0.010,            # estimado $10/1000 seg video
    "dalle_images": 0.040,             # DALL-E 3 standard: $0.04/image
    "publish_requests": 0.0,           # sem custo direto
}


def check_quota(db: Session, org_id: str, resource_type: str) -> None:
    """
    Verifica se a org ainda tem quota disponivel para o recurso no mes corrente.
    Lanca HTTPException 429 se o limite foi atingido.
    resource_type: 'video' | 'avatar'
    """
    from app.models.organization import Organization
    org = db.get(Organization, org_id)
    if not org:
        return

    quotas = PLAN_QUOTAS.get(org.plan, _DEFAULT_QUOTA)
    limit = quotas.get(resource_type)
    if limit is None:
        return  # ilimitado

    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = db.exec(
        select(func.count(UsageLog.id)).where(
            UsageLog.org_id == org_id,
            UsageLog.resource_type == resource_type,
            UsageLog.created_at >= first_of_month,
        )
    ).one()

    if used >= limit:
        plan_label = org.plan.replace("_", " ").title()
        raise HTTPException(
            status_code=429,
            detail=(
                f"Limite mensal de {limit} {'vídeos' if resource_type == 'video' else 'avatares'} "
                f"atingido para o plano {plan_label}. "
                f"Faça upgrade para continuar gerando."
            ),
        )


def get_quota_status(db: Session, org_id: str) -> dict:
    """Retorna uso atual e limite para cada recurso com quota."""
    from app.models.organization import Organization
    org = db.get(Organization, org_id)
    if not org:
        return {}

    quotas = PLAN_QUOTAS.get(org.plan, _DEFAULT_QUOTA)
    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = {}
    for resource_type, limit in quotas.items():
        used = db.exec(
            select(func.count(UsageLog.id)).where(
                UsageLog.org_id == org_id,
                UsageLog.resource_type == resource_type,
                UsageLog.created_at >= first_of_month,
            )
        ).one()
        result[resource_type] = {"used": int(used), "limit": limit}

    return result


def _get_monthly_cost(db: Session, org_id: str) -> float:
    """Retorna o custo acumulado do mes corrente para a org."""
    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.coalesce(func.sum(UsageLog.cost_usd), 0.0)).where(
        UsageLog.org_id == org_id,
        UsageLog.created_at >= first_of_month,
    )
    return db.exec(stmt).one()


def _check_billing_alert(db: Session, org_id: str, monthly_cost: float, new_cost: float) -> None:
    """Verifica se o custo mensal cruzou o threshold e envia alerta aos admins."""
    from app.models.organization import Organization
    org = db.get(Organization, org_id)
    if not org or org.billing_alert_threshold is None:
        return

    threshold = org.billing_alert_threshold
    prev_cost = monthly_cost - new_cost

    # Dispara alerta apenas quando cruza o threshold (nao a cada log acima dele)
    if prev_cost < threshold <= monthly_cost:
        try:
            from app.models.user import User, OrgMember
            admins = list(db.exec(
                select(User)
                .join(OrgMember, OrgMember.user_id == User.id)
                .where(OrgMember.org_id == org_id, OrgMember.role.in_(("owner", "admin")))
            ).all())

            from app.services.push_service import send_push_to_users
            from app.services.email_service import send_email

            title = f"Alerta de Billing — ${monthly_cost:.2f} este mes"
            body = (
                f"O custo de uso de IA de '{org.name}' atingiu ${monthly_cost:.2f} este mes, "
                f"ultrapassando o limite configurado de ${threshold:.2f}."
            )

            send_push_to_users(admins, title, body, data={"type": "billing_alert", "org_id": org_id})

            for admin in admins:
                send_email(
                    admin.email,
                    f"Brand Brain: {title}",
                    f"<h3>{title}</h3><p>{body}</p><p><small>Brand Brain — Alerta automatico</small></p>",
                )

            logger.warning(
                "Billing alert para org %s: $%.4f >= threshold $%.2f",
                org_id, monthly_cost, threshold,
            )
        except Exception as e:
            logger.error("Erro ao enviar billing alert: %s", e)


def log_usage(
    db: Session,
    org_id: str,
    resource_type: str,
    provider: str,
    units: int,
    unit_type: str,
    cost_center_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> UsageLog:
    """Registra uso de um recurso, salva no DB e verifica billing alert."""
    cost_key = f"{provider}_{unit_type}" if f"{provider}_{unit_type}" in UNIT_COSTS else provider
    cost_usd = units * UNIT_COSTS.get(cost_key, 0.0)

    entry = UsageLog(
        org_id=org_id,
        cost_center_id=cost_center_id,
        user_id=user_id,
        resource_type=resource_type,
        provider=provider,
        units=units,
        unit_type=unit_type,
        cost_usd=cost_usd,
        metadata_json=metadata or {},
    )
    db.add(entry)
    db.commit()
    logger.debug("Usage logged: %s/%s %d %s = $%.6f", resource_type, provider, units, unit_type, cost_usd)

    # Verificar threshold de billing (best-effort, nao bloqueia o caller)
    try:
        monthly_cost = _get_monthly_cost(db, org_id)
        _check_billing_alert(db, org_id, monthly_cost, cost_usd)
    except Exception as e:
        logger.warning("Erro ao verificar billing alert: %s", e)

    return entry
