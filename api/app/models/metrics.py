import uuid
from datetime import datetime
from datetime import date as date_type

from sqlmodel import SQLModel, Field


class MetricsDaily(SQLModel, table=True):
    __tablename__ = "metrics_daily"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content_item_id: str = Field(foreign_key="content_items.id", index=True)
    date: date_type = Field(index=True)
    impressions: int = Field(default=0)
    likes: int = Field(default=0)
    comments: int = Field(default=0)
    shares: int = Field(default=0)
    clicks: int = Field(default=0)
    followers_delta: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
