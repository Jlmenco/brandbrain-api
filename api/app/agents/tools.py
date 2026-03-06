"""Agent Tools — Internal functions available to agents.

Each tool is a simple function that operates on the database.
All tools generate audit logs.
"""

from sqlmodel import Session, select

from app.models.influencer import Influencer, BrandKit
from app.models.content import ContentItem, MacroContent
from app.models.tracking import TrackingLink
from app.models.market import MarketSource, Competitor, MarketFinding, MarketBrief, ContentBrief
from app.services.audit_service import log_action
from app.services.tracking_service import generate_slug, build_utm


# --- Tenancy tools ---

def tool_list_cost_centers(db: Session, org_id: str) -> list:
    from app.models.cost_center import CostCenter
    return db.exec(select(CostCenter).where(CostCenter.org_id == org_id)).all()


def tool_get_cost_center(db: Session, cc_id: str):
    from app.models.cost_center import CostCenter
    return db.get(CostCenter, cc_id)


# --- Influencer tools ---

def tool_create_influencer(db: Session, org_id: str, actor_user_id: str, **kwargs) -> Influencer:
    inf = Influencer(org_id=org_id, **kwargs)
    db.add(inf)
    db.flush()
    log_action(db, org_id, kwargs.get("cost_center_id"), actor_user_id, "create_influencer", "influencer", inf.id)
    return inf


def tool_update_influencer(db: Session, influencer_id: str, actor_user_id: str, **kwargs) -> Influencer:
    inf = db.get(Influencer, influencer_id)
    if not inf:
        raise ValueError("Influencer not found")
    for k, v in kwargs.items():
        if v is not None:
            setattr(inf, k, v)
    db.add(inf)
    db.flush()
    log_action(db, inf.org_id, inf.cost_center_id, actor_user_id, "update_influencer", "influencer", inf.id)
    return inf


def tool_upsert_brand_kit(db: Session, influencer_id: str, actor_user_id: str, **kwargs) -> BrandKit:
    existing = db.exec(select(BrandKit).where(BrandKit.influencer_id == influencer_id)).first()
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        db.add(existing)
        db.flush()
        return existing
    bk = BrandKit(influencer_id=influencer_id, **kwargs)
    db.add(bk)
    db.flush()
    inf = db.get(Influencer, influencer_id)
    log_action(db, inf.org_id if inf else "", None, actor_user_id, "upsert_brand_kit", "brand_kit", bk.id)
    return bk


# --- Content tools ---

def tool_create_content_item(db: Session, org_id: str, actor_user_id: str, **kwargs) -> ContentItem:
    ci = ContentItem(**kwargs)
    db.add(ci)
    db.flush()
    log_action(db, org_id, kwargs.get("cost_center_id"), actor_user_id, "create_content_item", "content_item", ci.id)
    return ci


def tool_submit_for_review(db: Session, org_id: str, content_item_id: str, actor_user_id: str) -> ContentItem:
    ci = db.get(ContentItem, content_item_id)
    if not ci:
        raise ValueError("Content item not found")
    ci.status = "review"
    db.add(ci)
    db.flush()
    log_action(db, org_id, ci.cost_center_id, actor_user_id, "submit_for_review", "content_item", ci.id)
    return ci


# --- Tracking tools ---

def tool_create_tracking_link(db: Session, actor_user_id: str, **kwargs) -> TrackingLink:
    utm = build_utm("social", kwargs.get("campaign_name", ""), kwargs.get("content_item_id", ""))
    tl = TrackingLink(
        cost_center_id=kwargs["cost_center_id"],
        content_item_id=kwargs.get("content_item_id"),
        slug=generate_slug(),
        destination_url=kwargs["destination_url"],
        utm=utm,
    )
    db.add(tl)
    db.flush()
    return tl


# --- Market tools ---

def tool_create_market_finding(db: Session, actor_user_id: str, **kwargs) -> MarketFinding:
    finding = MarketFinding(**kwargs)
    db.add(finding)
    db.flush()
    return finding


def tool_create_content_brief(db: Session, actor_user_id: str, **kwargs) -> ContentBrief:
    cb = ContentBrief(**kwargs)
    db.add(cb)
    db.flush()
    return cb
