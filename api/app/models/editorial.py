"""Editorial Planning models — AI-generated content calendars."""
import uuid
from datetime import datetime, date as date_type
from typing import Optional

from sqlmodel import SQLModel, Field


class EditorialPlan(SQLModel, table=True):
    __tablename__ = "editorial_plans"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id", index=True)
    period_type: str = Field(default="week")  # week | month
    period_start: date_type
    period_end: date_type
    status: str = Field(default="draft")  # draft | approved | archived
    ai_rationale: Optional[str] = Field(default=None)
    created_by: Optional[str] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EditorialSlot(SQLModel, table=True):
    __tablename__ = "editorial_slots"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    plan_id: str = Field(foreign_key="editorial_plans.id", index=True)
    date: date_type
    time_slot: str = Field(default="morning")  # morning | afternoon | evening
    platform: str  # linkedin | instagram | twitter | ...
    pillar: str  # Educação | Prova Social | Bastidores | Oferta | Comunidade
    theme: str
    objective: str = Field(default="awareness")
    content_item_id: Optional[str] = Field(default=None, foreign_key="content_items.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
