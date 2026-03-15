import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class DripCampaign(SQLModel, table=True):
    """Campanha de drip email com sequencia de steps automaticos."""
    __tablename__ = "drip_campaigns"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: Optional[str] = Field(default=None, foreign_key="organizations.id", index=True)
    name: str
    trigger_event: str  # welcome | trial_expiring | inactive | custom
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DripStep(SQLModel, table=True):
    """Step individual de uma campanha drip (subject + body + delay)."""
    __tablename__ = "drip_steps"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    campaign_id: str = Field(foreign_key="drip_campaigns.id", index=True)
    step_order: int = Field(default=0)
    delay_hours: int = Field(default=0)  # horas apos o step anterior (ou enrollment)
    subject: str = ""
    body_template: str = ""  # HTML com placeholders {name}, {org_name}, {upgrade_url}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DripEnrollment(SQLModel, table=True):
    """Inscricao de um usuario em uma campanha drip."""
    __tablename__ = "drip_enrollments"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    campaign_id: str = Field(foreign_key="drip_campaigns.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    org_id: Optional[str] = Field(default=None, foreign_key="organizations.id", index=True)
    current_step: int = Field(default=0)  # indice do proximo step a enviar
    status: str = Field(default="active")  # active | completed | cancelled
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    next_send_at: Optional[datetime] = Field(default=None, index=True)
    completed_at: Optional[datetime] = Field(default=None)
