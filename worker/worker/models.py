"""
Minimal model definitions for the worker.
Mirrored from apps/api/app/models/content.py and apps/api/app/models/audit.py.
Keep in sync with the API models when schema changes occur.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class ContentItem(SQLModel, table=True):
    __tablename__ = "content_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    cost_center_id: str = Field(index=True)
    influencer_id: str = ""
    campaign_id: Optional[str] = None
    source_macro_id: Optional[str] = None
    provider_target: str = ""
    text: str = ""
    media_refs: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    status: str = Field(default="draft", index=True)
    scheduled_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    provider_post_id: Optional[str] = None
    provider_post_url: Optional[str] = None
    version: int = Field(default=1)
    retry_count: int = Field(default=0)
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    video_job_status: Optional[str] = Field(default=None)
    video_job_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(index=True)
    cost_center_id: str = Field(index=True)
    provider: str = ""  # meta | linkedin | x | tiktok | youtube
    account_name: str = ""
    account_id: str = ""
    scopes: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    token_encrypted: str = ""
    refresh_token_encrypted: str = ""
    token_expires_at: Optional[datetime] = None
    status: str = Field(default="connected")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(index=True)
    cost_center_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    action: str = ""
    target_type: str = ""
    target_id: str = ""
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)
