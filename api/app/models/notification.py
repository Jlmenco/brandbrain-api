import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    type: str = "status_change"
    title: str = ""
    body: str = ""
    target_type: str = ""
    target_id: str = ""
    is_read: bool = Field(default=False)
    email_sent: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
