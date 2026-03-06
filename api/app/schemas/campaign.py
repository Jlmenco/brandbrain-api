from pydantic import BaseModel
from typing import Optional
from datetime import date

class CampaignCreate(BaseModel):
    cost_center_id: str
    name: str
    objective: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class CampaignResponse(BaseModel):
    id: str
    cost_center_id: str
    name: str
    objective: str
    start_date: Optional[date]
    end_date: Optional[date]
