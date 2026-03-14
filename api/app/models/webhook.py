import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class WebhookConfig(SQLModel, table=True):
    """Configuracoes de webhook por organizacao (Slack, Discord, Teams, Custom)."""
    __tablename__ = "webhook_configs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    name: str = ""              # Ex: "Slack #marketing"
    provider: str = ""          # slack | discord | teams | custom
    url: str = ""               # Webhook URL
    events: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    # events: ["submit_review", "approve", "reject", "schedule", "publish_now"]
    is_active: bool = Field(default=True)
    created_by: Optional[str] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
