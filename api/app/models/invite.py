import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class OrgInvite(SQLModel, table=True):
    __tablename__ = "org_invites"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    invited_by: str = Field(foreign_key="users.id")
    email: str = Field(index=True)
    role: str = Field(default="editor")  # owner | admin | editor | viewer
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    accepted_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
