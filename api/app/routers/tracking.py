from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.tracking import TrackingLink, Event
from app.schemas.tracking import TrackingLinkCreate, TrackingLinkResponse, EventCreate
from app.dependencies import get_current_user
from app.services.tracking_service import generate_slug, build_utm

router = APIRouter()


@router.post("/links", response_model=TrackingLinkResponse)
def create_tracking_link(body: TrackingLinkCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    utm = build_utm("social", body.campaign_name, body.content_item_id or "")
    tl = TrackingLink(
        cost_center_id=body.cost_center_id,
        content_item_id=body.content_item_id,
        slug=generate_slug(),
        destination_url=body.destination_url,
        utm=utm,
    )
    db.add(tl)
    db.commit()
    db.refresh(tl)
    return tl


@router.get("/links", response_model=list[TrackingLinkResponse])
def list_tracking_links(cc_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(TrackingLink).where(TrackingLink.cost_center_id == cc_id)).all()


@router.post("/events/click")
def track_click(body: EventCreate, db: Session = Depends(get_session)):
    event = Event(**body.model_dump())
    event.type = "click"
    db.add(event)
    db.commit()
    return {"detail": "Click tracked"}


@router.post("/events/lead")
def track_lead(body: EventCreate, db: Session = Depends(get_session)):
    event = Event(**body.model_dump())
    event.type = "lead"
    db.add(event)
    db.commit()
    return {"detail": "Lead event tracked"}
