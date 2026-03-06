from pydantic import BaseModel
from typing import Optional

class TrackingLinkCreate(BaseModel):
    cost_center_id: str
    content_item_id: Optional[str] = None
    destination_url: str
    campaign_name: str = ""

class TrackingLinkResponse(BaseModel):
    id: str
    cost_center_id: str
    slug: str
    destination_url: str
    utm: dict

class EventCreate(BaseModel):
    org_id: str
    cost_center_id: str
    type: str  # click | lead | conversion
    tracking_link_id: Optional[str] = None
    metadata_json: dict = {}

class LeadCreate(BaseModel):
    cost_center_id: str
    source: str = "manual"
    name: str = ""
    email: str = ""
    phone: str = ""
    score: int = 0

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    score: Optional[int] = None
    status: Optional[str] = None

class LeadResponse(BaseModel):
    id: str
    cost_center_id: str
    source: str
    name: str
    email: str
    phone: str
    score: int
    status: str
