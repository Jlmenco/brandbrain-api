from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.cost_center import CostCenter
from app.schemas.cost_center import CostCenterCreate, CostCenterUpdate, CostCenterResponse
from app.dependencies import get_current_user, check_role, ADMIN_ROLES

router = APIRouter()


@router.get("", response_model=list[CostCenterResponse])
def list_cost_centers(org_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(CostCenter).where(CostCenter.org_id == org_id)).all()


@router.post("", response_model=CostCenterResponse)
def create_cost_center(body: CostCenterCreate, org_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    cc = CostCenter(org_id=org_id, **body.model_dump())
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc


@router.get("/{cc_id}", response_model=CostCenterResponse)
def get_cost_center(cc_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    cc = db.get(CostCenter, cc_id)
    if not cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    return cc


@router.patch("/{cc_id}", response_model=CostCenterResponse)
def update_cost_center(cc_id: str, body: CostCenterUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    cc = db.get(CostCenter, cc_id)
    if not cc:
        raise HTTPException(status_code=404, detail="Cost center not found")
    check_role(db, current_user.id, cc.org_id, ADMIN_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(cc, key, val)
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc
