import uuid
from datetime import datetime

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text
from pgvector.sqlalchemy import Vector


class BrandKitEmbedding(SQLModel, table=True):
    __tablename__ = "brand_kit_embeddings"
    model_config = {"protected_namespaces": ()}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    brand_kit_id: str = Field(foreign_key="brand_kits.id", index=True)
    influencer_id: str = Field(foreign_key="influencers.id", index=True)
    chunk_type: str = ""  # influencer_profile | description | value_props | products | audience | style_guidelines | links
    chunk_text: str = Field(sa_column=Column(Text, nullable=False, default=""))
    embedding: list = Field(sa_column=Column(Vector(1536)))  # text-embedding-3-small = 1536 dims
    model_name: str = Field(default="text-embedding-3-small")
    created_at: datetime = Field(default_factory=datetime.utcnow)
