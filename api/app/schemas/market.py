from pydantic import BaseModel
from typing import Optional
from datetime import date

class MarketSourceCreate(BaseModel):
    org_id: str
    cost_center_id: Optional[str] = None
    name: str
    type: str  # rss | website | report | trends
    url: str
    tags: list = []

class MarketSourceResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: Optional[str]
    name: str
    type: str
    url: str
    tags: list
    is_active: bool

class CompetitorCreate(BaseModel):
    org_id: str
    cost_center_id: str
    name: str
    website_url: str = ""
    social_handles: dict = {}
    notes: str = ""

class CompetitorResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: str
    name: str
    website_url: str
    social_handles: dict = {}
    notes: str

class MarketFindingResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: Optional[str]
    title: str
    summary: str
    tags: list
    source_url: str
    confidence: float
    type: str

class MarketBriefResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: Optional[str]
    week_start: date
    week_end: date
    content: dict

class MarketRunRequest(BaseModel):
    org_id: str
    cc_id: Optional[str] = None
    keywords: list[str] = []

class MarketRunResponse(BaseModel):
    findings_created: int
    findings: list[dict]

class WeeklyBriefRequest(BaseModel):
    org_id: str
    cc_id: Optional[str] = None

class WeeklyBriefResponse(BaseModel):
    brief_id: str
    content: dict
    content_briefs_created: int
