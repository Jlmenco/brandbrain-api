from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: Optional[str]
    actor_user_id: Optional[str]
    action: str
    target_type: str
    target_id: str
    metadata_json: dict = {}
    created_at: datetime


class PaginatedAuditResponse(BaseModel):
    items: list[AuditLogResponse] = []
    total: int = 0
