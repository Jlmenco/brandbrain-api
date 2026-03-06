from pydantic import BaseModel
from typing import Optional

class CostCenterCreate(BaseModel):
    name: str
    code: str
    monthly_budget_media: float = 0.0
    monthly_budget_ai: float = 0.0

class CostCenterUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    monthly_budget_media: Optional[float] = None
    monthly_budget_ai: Optional[float] = None

class CostCenterResponse(BaseModel):
    id: str
    org_id: str
    name: str
    code: str
    monthly_budget_media: float
    monthly_budget_ai: float
