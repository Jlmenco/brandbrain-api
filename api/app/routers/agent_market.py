from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.market import MarketSource, Competitor, MarketFinding, MarketBrief
from app.schemas.market import (
    MarketSourceCreate, MarketSourceResponse,
    CompetitorCreate, CompetitorResponse,
    MarketFindingResponse, MarketBriefResponse,
    MarketRunRequest, MarketRunResponse,
    WeeklyBriefRequest, WeeklyBriefResponse,
)
from app.dependencies import get_current_user
from app.agents.market_agent import run_market_collection, run_weekly_brief

router = APIRouter()


@router.post("/run", response_model=MarketRunResponse)
def run_market(body: MarketRunRequest, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return run_market_collection(db, current_user, body)


@router.post("/weekly-brief", response_model=WeeklyBriefResponse)
def weekly_brief(body: WeeklyBriefRequest, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return run_weekly_brief(db, current_user, body)


@router.get("/findings", response_model=list[MarketFindingResponse])
def list_findings(cc_id: str = Query(None), from_date: str = Query(None), to_date: str = Query(None), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    stmt = select(MarketFinding)
    if cc_id:
        stmt = stmt.where(MarketFinding.cost_center_id == cc_id)
    return db.exec(stmt).all()


@router.get("/briefs", response_model=list[MarketBriefResponse])
def list_briefs(cc_id: str = Query(None), db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    stmt = select(MarketBrief)
    if cc_id:
        stmt = stmt.where(MarketBrief.cost_center_id == cc_id)
    return db.exec(stmt).all()


@router.post("/sources", response_model=MarketSourceResponse)
def create_source(body: MarketSourceCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    src = MarketSource(**body.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


@router.post("/competitors", response_model=CompetitorResponse)
def create_competitor(body: CompetitorCreate, db: Session = Depends(get_session), current_user=Depends(get_current_user)):
    comp = Competitor(**body.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp
