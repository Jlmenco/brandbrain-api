import uuid
from datetime import datetime
from datetime import date as date_type
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class MarketSource(SQLModel, table=True):
    __tablename__ = "market_sources"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id")
    name: str = ""
    type: str = ""  # rss | website | report | trends
    url: str = ""
    tags: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Competitor(SQLModel, table=True):
    __tablename__ = "competitors"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    name: str = ""
    website_url: str = ""
    social_handles: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketFinding(SQLModel, table=True):
    __tablename__ = "market_findings"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id")
    title: str = ""
    summary: str = ""
    tags: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    source_url: str = ""
    source_published_at: Optional[datetime] = None
    extracted_evidence: str = ""
    confidence: float = Field(default=0.0)  # 0..1
    type: str = ""  # trend | competitor | faq | opportunity | risk
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketBrief(SQLModel, table=True):
    __tablename__ = "market_briefs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id")
    week_start: date_type
    week_end: date_type
    content: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentBrief(SQLModel, table=True):
    __tablename__ = "content_briefs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id")
    based_on_finding_ids: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    title: str = ""
    thesis: str = ""
    arguments: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    proof: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    format_suggestions: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    cta_suggestion: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
