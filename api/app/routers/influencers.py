from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.influencer import Influencer, BrandKit
from app.schemas.influencer import (
    InfluencerCreate, InfluencerUpdate, InfluencerResponse,
    BrandKitCreate, BrandKitResponse,
)
from app.dependencies import get_current_user, check_role, ADMIN_ROLES

router = APIRouter()


@router.get("", response_model=list[InfluencerResponse])
def list_influencers(org_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(Influencer).where(Influencer.org_id == org_id)).all()


@router.post("", response_model=InfluencerResponse)
def create_influencer(body: InfluencerCreate, org_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    check_role(db, current_user.id, org_id, ADMIN_ROLES)
    inf = Influencer(org_id=org_id, **body.model_dump())
    db.add(inf)
    db.commit()
    db.refresh(inf)
    return inf


@router.get("/{influencer_id}", response_model=InfluencerResponse)
def get_influencer(influencer_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return inf


@router.patch("/{influencer_id}", response_model=InfluencerResponse)
def update_influencer(influencer_id: str, body: InfluencerUpdate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    check_role(db, current_user.id, inf.org_id, ADMIN_ROLES)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(inf, key, val)
    db.add(inf)
    db.commit()
    db.refresh(inf)
    return inf


@router.post("/{influencer_id}/brand-kit", response_model=BrandKitResponse)
def upsert_brand_kit(influencer_id: str, body: BrandKitCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    check_role(db, current_user.id, inf.org_id, ADMIN_ROLES)
    existing = db.exec(select(BrandKit).where(BrandKit.influencer_id == influencer_id)).first()
    if existing:
        for key, val in body.model_dump().items():
            setattr(existing, key, val)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        _auto_embed(db, influencer_id)
        return existing
    bk = BrandKit(influencer_id=influencer_id, **body.model_dump())
    db.add(bk)
    db.commit()
    db.refresh(bk)
    _auto_embed(db, influencer_id)
    return bk


def _auto_embed(db: Session, influencer_id: str):
    """Auto-embed brand kit content after upsert. Failure does not block save."""
    try:
        from app.services.embedding_service import get_embedding_service
        svc = get_embedding_service()
        svc.embed_brand_kit(db, influencer_id)
        db.commit()
    except Exception:
        db.rollback()


@router.get("/{influencer_id}/brand-kit", response_model=BrandKitResponse)
def get_brand_kit(influencer_id: str, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == influencer_id)).first()
    if not bk:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    return bk
