from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.tracking import Lead
from app.models.cost_center import CostCenter
from app.schemas.tracking import LeadCreate, LeadUpdate, LeadResponse
from app.dependencies import get_current_user, check_role, EDITOR_ROLES
from app.services.audit_service import log_action

router = APIRouter()


def _get_org_id(db: Session, cost_center_id: str) -> str:
    cc = db.get(CostCenter, cost_center_id)
    if not cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    return cc.org_id


@router.get("", response_model=list[LeadResponse])
def list_leads(cc_id: str = Query(...), status: str = Query(None), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    stmt = select(Lead).where(Lead.cost_center_id == cc_id)
    if status:
        stmt = stmt.where(Lead.status == status)
    return db.exec(stmt).all()


@router.post("", response_model=LeadResponse)
def create_lead(body: LeadCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org_id = _get_org_id(db, body.cost_center_id)
    check_role(db, current_user.id, org_id, EDITOR_ROLES)
    lead = Lead(**body.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    log_action(db, org_id, lead.cost_center_id, current_user.id, "create", "lead", lead.id)
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, body: LeadUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    org_id = _get_org_id(db, lead.cost_center_id)
    check_role(db, current_user.id, org_id, EDITOR_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(lead, key, val)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    log_action(db, org_id, lead.cost_center_id, current_user.id, "update", "lead", lead.id)
    return lead
