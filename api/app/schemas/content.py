from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MacroContentCreate(BaseModel):
    org_id: str
    influencer_master_id: str
    theme: str
    content_raw: str
    content_structured: dict = {}

class MacroContentUpdate(BaseModel):
    theme: Optional[str] = None
    content_raw: Optional[str] = None
    content_structured: Optional[dict] = None
    status: Optional[str] = None

class MacroContentResponse(BaseModel):
    id: str
    org_id: str
    influencer_master_id: str
    theme: str
    content_raw: str
    content_structured: dict = {}
    status: str

class RedistributeRequest(BaseModel):
    targets: list[str]  # cost center ids
    provider_targets: list[str]  # linkedin, instagram, etc
    mode: str = "create_drafts"

class ContentItemCreate(BaseModel):
    cost_center_id: str
    influencer_id: str
    campaign_id: Optional[str] = None
    provider_target: str
    text: str
    media_refs: list = []

class ContentItemUpdate(BaseModel):
    text: Optional[str] = None
    media_refs: Optional[list] = None
    provider_target: Optional[str] = None

class ContentItemResponse(BaseModel):
    id: str
    cost_center_id: str
    influencer_id: str
    campaign_id: Optional[str]
    source_macro_id: Optional[str]
    provider_target: str
    text: str
    media_refs: list = []
    status: str
    scheduled_at: Optional[datetime]
    posted_at: Optional[datetime]
    provider_post_id: Optional[str]
    provider_post_url: Optional[str] = None
    version: int
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None

class PaginatedContentResponse(BaseModel):
    items: list[ContentItemResponse] = []
    total: int = 0

class ScheduleRequest(BaseModel):
    scheduled_at: datetime
