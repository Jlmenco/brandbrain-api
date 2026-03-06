import uuid
from datetime import datetime

from sqlmodel import SQLModel, Field


class CostCenter(SQLModel, table=True):
    __tablename__ = "cost_centers"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    name: str
    code: str = Field(index=True)  # e.g. MELPURA, MEATFRIENDS
    monthly_budget_media: float = Field(default=0.0)
    monthly_budget_ai: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
