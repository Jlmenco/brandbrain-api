import uuid
from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    name: str
    objective: str = ""  # leads | awareness | traffic
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
