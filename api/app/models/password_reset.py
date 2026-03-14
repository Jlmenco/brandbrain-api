import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
