from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.content import MacroContent, ContentItem
from app.models.influencer import Influencer
from app.schemas.content import MacroContentCreate, MacroContentUpdate, MacroContentResponse, RedistributeRequest
from app.dependencies import get_current_user

router = APIRouter()


@router.get("", response_model=list[MacroContentResponse])
def list_macro_contents(org_id: str = Query(...), status: str = Query(None), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    stmt = select(MacroContent).where(MacroContent.org_id == org_id)
    if status:
        stmt = stmt.where(MacroContent.status == status)
    return db.exec(stmt).all()


@router.post("", response_model=MacroContentResponse)
def create_macro_content(body: MacroContentCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    mc = MacroContent(**body.model_dump())
    db.add(mc)
    db.commit()
    db.refresh(mc)
    return mc


@router.get("/{macro_id}", response_model=MacroContentResponse)
def get_macro_content(macro_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    mc = db.get(MacroContent, macro_id)
    if not mc:
        raise HTTPException(status_code=404, detail="Macro content not found")
    return mc


@router.patch("/{macro_id}", response_model=MacroContentResponse)
def update_macro_content(macro_id: str, body: MacroContentUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    mc = db.get(MacroContent, macro_id)
    if not mc:
        raise HTTPException(status_code=404, detail="Macro content not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(mc, key, val)
    db.add(mc)
    db.commit()
    db.refresh(mc)
    return mc


@router.post("/{macro_id}/redistribute")
def redistribute(macro_id: str, body: RedistributeRequest, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    mc = db.get(MacroContent, macro_id)
    if not mc:
        raise HTTPException(status_code=404, detail="Macro content not found")

    created_ids = []
    for cc_id in body.targets:
        # Find influencer for this cost center
        inf = db.exec(select(Influencer).where(Influencer.cost_center_id == cc_id).where(Influencer.is_active == True)).first()
        if not inf:
            continue
        for provider in body.provider_targets:
            ci = ContentItem(
                cost_center_id=cc_id,
                influencer_id=inf.id,
                source_macro_id=mc.id,
                provider_target=provider,
                text=f"[AI-ADAPTED] {mc.content_raw}",
                status="draft",
            )
            db.add(ci)
            db.flush()
            created_ids.append(ci.id)
    db.commit()
    return {"created_content_items": created_ids, "count": len(created_ids)}
