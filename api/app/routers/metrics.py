from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from datetime import date

from app.database import get_session
from app.models.metrics import MetricsDaily
from app.models.content import ContentItem
from app.schemas.metrics import MetricsDailyResponse, MetricsOverview
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/daily", response_model=list[MetricsDailyResponse])
def get_daily_metrics(cc_id: str = Query(...), from_date: date = Query(None), to_date: date = Query(None), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    # Join with content_items to filter by cc_id
    stmt = select(MetricsDaily).join(ContentItem, MetricsDaily.content_item_id == ContentItem.id).where(ContentItem.cost_center_id == cc_id)
    if from_date:
        stmt = stmt.where(MetricsDaily.date >= from_date)
    if to_date:
        stmt = stmt.where(MetricsDaily.date <= to_date)
    return db.exec(stmt).all()


@router.get("/by-content", response_model=list[MetricsDailyResponse])
def get_metrics_by_content(content_id: str = Query(...), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return db.exec(select(MetricsDaily).where(MetricsDaily.content_item_id == content_id)).all()


@router.get("/overview", response_model=MetricsOverview)
def get_overview(cc_id: str = Query(...), from_date: date = Query(None), to_date: date = Query(None), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    stmt = select(
        func.coalesce(func.sum(MetricsDaily.impressions), 0),
        func.coalesce(func.sum(MetricsDaily.likes), 0),
        func.coalesce(func.sum(MetricsDaily.comments), 0),
        func.coalesce(func.sum(MetricsDaily.shares), 0),
        func.coalesce(func.sum(MetricsDaily.clicks), 0),
        func.coalesce(func.sum(MetricsDaily.followers_delta), 0),
        func.count(func.distinct(MetricsDaily.content_item_id)),
    ).join(
        ContentItem, MetricsDaily.content_item_id == ContentItem.id
    ).where(
        ContentItem.cost_center_id == cc_id
    )
    if from_date:
        stmt = stmt.where(MetricsDaily.date >= from_date)
    if to_date:
        stmt = stmt.where(MetricsDaily.date <= to_date)
    row = db.exec(stmt).first()
    if row is None:
        return MetricsOverview()
    return MetricsOverview(
        total_impressions=row[0],
        total_likes=row[1],
        total_comments=row[2],
        total_shares=row[3],
        total_clicks=row[4],
        total_followers_delta=row[5],
        total_posts=row[6],
    )
