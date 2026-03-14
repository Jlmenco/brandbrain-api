import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class UsageLog(SQLModel, table=True):
    """Rastreia uso de recursos de IA e publicacao por org/cost_center para billing."""
    __tablename__ = "usage_logs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(default=None, foreign_key="cost_centers.id", index=True)
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    resource_type: str = ""  # ai_generation | tts | video | avatar | publish
    provider: str = ""       # openai | anthropic | elevenlabs | hedra | dall-e
    units: int = Field(default=0)         # tokens, segundos de audio, segundos de video, etc.
    unit_type: str = ""      # tokens | audio_seconds | video_seconds | images | requests
    cost_usd: float = Field(default=0.0)  # custo estimado em USD
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)
