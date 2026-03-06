import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    provider: str = ""  # meta | linkedin | x | tiktok | youtube
    account_name: str = ""
    account_id: str = ""
    scopes: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    token_encrypted: str = ""
    refresh_token_encrypted: str = ""
    token_expires_at: Optional[datetime] = None
    status: str = Field(default="connected")  # connected | revoked | expired
    created_at: datetime = Field(default_factory=datetime.utcnow)
