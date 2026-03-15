import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


ONBOARDING_STEPS = [
    "profile_setup",
    "first_influencer",
    "brand_kit",
    "first_content",
    "first_publish",
    "connect_social",
]


class OnboardingProgress(SQLModel, table=True):
    """Progresso do onboarding guiado por usuario/org."""
    __tablename__ = "onboarding_progress"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    steps_completed: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    is_dismissed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
