import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class ContentTemplate(SQLModel, table=True):
    __tablename__ = "content_templates"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    name: str
    description: str = ""
    provider_target: str = ""  # linkedin | instagram | facebook | tiktok | youtube | "" (todos)
    text_template: str = ""    # Texto com placeholders {{brand_name}}, {{cta}}, etc.
    tags: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    is_active: bool = Field(default=True)
    created_by: Optional[str] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
