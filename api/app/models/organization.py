import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    # Perfil: solo | agency | group
    account_type: str = Field(default="agency")
    # Para perfil Group: referencia para org mae
    parent_org_id: Optional[str] = Field(default=None, foreign_key="organizations.id", index=True)
    # Alerta de billing: envia notificacao quando custo mensal ultrapassar este valor (USD)
    billing_alert_threshold: Optional[float] = Field(default=None)
    # Plano: trial | solo_monthly | agency_monthly | group_monthly | active
    plan: str = Field(default="active")
    # Data de expiracao do trial (None = sem trial ativo)
    trial_ends_at: Optional[datetime] = Field(default=None)
    # ID do cliente no Asaas (preenchido no primeiro checkout)
    asaas_customer_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
