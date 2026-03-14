"""Endpoint de consulta de uso/billing por org."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.usage import UsageLog
from app.dependencies import get_current_user, check_role, ADMIN_ROLES

logger = logging.getLogger("app.usage")

router = APIRouter()


class UsageSummary(BaseModel):
    resource_type: str
    provider: str
    total_units: int
    unit_type: str
    total_cost_usd: float
    request_count: int


class UsageOverview(BaseModel):
    total_cost_usd: float
    by_resource: list[UsageSummary]
    period_start: str
    period_end: str


@router.get("/overview", response_model=UsageOverview)
def get_usage_overview(
    org_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    check_role(db, current_user.id, org_id, ADMIN_ROLES)

    since = datetime.utcnow() - timedelta(days=days)

    rows = db.exec(
        select(
            UsageLog.resource_type,
            UsageLog.provider,
            UsageLog.unit_type,
            func.sum(UsageLog.units).label("total_units"),
            func.sum(UsageLog.cost_usd).label("total_cost_usd"),
            func.count(UsageLog.id).label("request_count"),
        )
        .where(UsageLog.org_id == org_id, UsageLog.created_at >= since)
        .group_by(UsageLog.resource_type, UsageLog.provider, UsageLog.unit_type)
        .order_by(func.sum(UsageLog.cost_usd).desc())
    ).all()

    by_resource = [
        UsageSummary(
            resource_type=r[0],
            provider=r[1],
            unit_type=r[2],
            total_units=int(r[3] or 0),
            total_cost_usd=float(r[4] or 0),
            request_count=int(r[5] or 0),
        )
        for r in rows
    ]

    total_cost = sum(r.total_cost_usd for r in by_resource)

    return UsageOverview(
        total_cost_usd=total_cost,
        by_resource=by_resource,
        period_start=since.date().isoformat(),
        period_end=datetime.utcnow().date().isoformat(),
    )


@router.get("/quota")
def get_quota(
    org_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Retorna uso e limite de quota de recursos para o mes corrente."""
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    from app.services.usage_service import get_quota_status
    return get_quota_status(db, org_id)


@router.get("/logs")
def list_usage_logs(
    org_id: str = Query(...),
    resource_type: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    stmt = select(UsageLog).where(UsageLog.org_id == org_id)
    if resource_type:
        stmt = stmt.where(UsageLog.resource_type == resource_type)
    stmt = stmt.order_by(UsageLog.created_at.desc()).offset(skip).limit(limit)
    return db.exec(stmt).all()
