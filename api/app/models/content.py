import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class MacroContent(SQLModel, table=True):
    __tablename__ = "macro_contents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    influencer_master_id: str = Field(foreign_key="influencers.id")
    theme: str = ""
    content_raw: str = ""
    content_structured: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    status: str = Field(default="draft")  # draft | ready | archived
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentItem(SQLModel, table=True):
    __tablename__ = "content_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    influencer_id: str = Field(foreign_key="influencers.id")
    campaign_id: Optional[str] = Field(default=None, foreign_key="campaigns.id")
    source_macro_id: Optional[str] = Field(
        default=None, foreign_key="macro_contents.id"
    )
    provider_target: str = ""  # linkedin | instagram | facebook | etc
    text: str = ""
    media_refs: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    status: str = Field(
        default="draft", index=True
    )  # draft | review | approved | scheduled | posted | failed | rejected
    scheduled_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    provider_post_id: Optional[str] = None
    provider_post_url: Optional[str] = None
    version: int = Field(default=1)
    retry_count: int = Field(default=0)
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    # Fila assincrona de geracao de video
    video_job_status: Optional[str] = Field(default=None)  # pending | processing | done | failed
    video_job_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Approval(SQLModel, table=True):
    __tablename__ = "approvals"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content_item_id: str = Field(foreign_key="content_items.id", index=True)
    reviewer_user_id: str = Field(foreign_key="users.id")
    decision: str = ""  # approve | request_changes | reject
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
