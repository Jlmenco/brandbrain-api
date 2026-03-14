import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class Influencer(SQLModel, table=True):
    __tablename__ = "influencers"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    cost_center_id: Optional[str] = Field(
        default=None, foreign_key="cost_centers.id", index=True
    )  # NULL = master influencer
    type: str = Field(default="brand")  # master | brand
    name: str
    niche: str = ""
    tone: str = ""
    emoji_level: str = Field(default="low")  # none | low | medium | high
    forbidden_topics: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    forbidden_words: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    allowed_words: list = Field(default_factory=list, sa_column=Column(JSON, default=list))
    cta_style: str = ""
    language: str = Field(default="pt-BR")
    voice_id: Optional[str] = Field(default=None)  # ElevenLabs voice ID
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BrandKit(SQLModel, table=True):
    __tablename__ = "brand_kits"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    influencer_id: str = Field(foreign_key="influencers.id", unique=True, index=True)
    description: str = ""
    value_props: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    products: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    audience: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    style_guidelines: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    links: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InfluencerAsset(SQLModel, table=True):
    __tablename__ = "influencer_assets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    influencer_id: str = Field(foreign_key="influencers.id", index=True)
    asset_type: str = ""  # avatar | logo | background | media
    storage_url: str = ""
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    created_at: datetime = Field(default_factory=datetime.utcnow)
