from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.campaign import Campaign
from app.models.cost_center import CostCenter
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from app.dependencies import get_current_user, check_role, ADMIN_ROLES
from app.services.audit_service import log_action

router = APIRouter()


def _get_org_id(db: Session, cost_center_id: str) -> str:
    cc = db.get(CostCenter, cost_center_id)
    if not cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    return cc.org_id


@router.get("", response_model=list[CampaignResponse])
def list_campaigns(cc_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(Campaign).where(Campaign.cost_center_id == cc_id)).all()


@router.post("", response_model=CampaignResponse)
def create_campaign(body: CampaignCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    org_id = _get_org_id(db, body.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    c = Campaign(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    log_action(db, org_id, c.cost_center_id, current_user.id, "create", "campaign", c.id)
    return c


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: str, body: CampaignUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    org_id = _get_org_id(db, c.cost_center_id)
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(c, key, val)
    db.add(c)
    db.commit()
    db.refresh(c)
    log_action(db, org_id, c.cost_center_id, current_user.id, "update", "campaign", c.id)
    return c
