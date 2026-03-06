import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class TrackingLink(SQLModel, table=True):
    __tablename__ = "tracking_links"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    content_item_id: Optional[str] = Field(
        default=None, foreign_key="content_items.id"
    )
    slug: str = Field(unique=True, index=True)
    destination_url: str = ""
    utm: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    type: str = ""  # click | lead | conversion
    tracking_link_id: Optional[str] = Field(
        default=None, foreign_key="tracking_links.id"
    )
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Lead(SQLModel, table=True):
    __tablename__ = "leads"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    cost_center_id: str = Field(foreign_key="cost_centers.id", index=True)
    source: str = ""  # form | whatsapp | dm | manual
    name: str = ""
    email: str = ""
    phone: str = ""
    score: int = Field(default=0)
    status: str = Field(default="new")  # new | qualified | won | lost
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)
