from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func

from app.database import get_session
from app.dependencies import get_current_user
from app.models.notification import Notification
from app.schemas.notification import PaginatedNotificationResponse, UnreadCountResponse

router = APIRouter()


class PushTokenBody(BaseModel):
    token: str


@router.post("/push-token")
def register_push_token(
    body: PushTokenBody,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Registra o Expo push token do dispositivo mobile para o usuario logado."""
    current_user.push_token = body.token
    db.add(current_user)
    db.commit()
    return {"ok": True}


@router.get("", response_model=PaginatedNotificationResponse)
def list_notifications(
    org_id: str = Query(...),
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.org_id == org_id,
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.exec(count_stmt).one()

    stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    items = db.exec(stmt).all()
    return {"items": items, "total": total}


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    org_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stmt = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.org_id == org_id,
        Notification.is_read == False,
    )
    count = db.exec(stmt).one()
    return {"count": count}


@router.patch("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.add(notif)
    db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_as_read(
    org_id: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.org_id == org_id,
        Notification.is_read == False,
    )
    notifications = db.exec(stmt).all()
    for notif in notifications:
        notif.is_read = True
        db.add(notif)
    db.commit()
    return {"ok": True, "count": len(notifications)}
