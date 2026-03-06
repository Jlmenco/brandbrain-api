from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from sqlalchemy import func

from app.database import get_session
from app.dependencies import get_current_user
from app.models.audit import AuditLog
from app.schemas.audit import PaginatedAuditResponse

router = APIRouter()


@router.get("", response_model=PaginatedAuditResponse)
def list_audit_logs(
    org_id: str = Query(...),
    cc_id: str = Query(None),
    action: str = Query(None),
    target_type: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stmt = select(AuditLog).where(AuditLog.org_id == org_id)
    if cc_id:
        stmt = stmt.where(AuditLog.cost_center_id == cc_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.exec(count_stmt).one()

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    items = db.exec(stmt).all()
    return {"items": items, "total": total}
