from pydantic import BaseModel
from typing import Optional

class InfluencerCreate(BaseModel):
    cost_center_id: Optional[str] = None
    type: str = "brand"  # master | brand
    name: str
    niche: str = ""
    tone: str = ""
    emoji_level: str = "low"
    forbidden_topics: list = []
    forbidden_words: list = []
    allowed_words: list = []
    cta_style: str = ""
    language: str = "pt-BR"
    voice_id: Optional[str] = None

class InfluencerUpdate(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    tone: Optional[str] = None
    emoji_level: Optional[str] = None
    forbidden_topics: Optional[list] = None
    forbidden_words: Optional[list] = None
    allowed_words: Optional[list] = None
    cta_style: Optional[str] = None
    is_active: Optional[bool] = None
    voice_id: Optional[str] = None

class InfluencerResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: Optional[str]
    type: str
    name: str
    niche: str
    tone: str
    emoji_level: str
    forbidden_topics: list = []
    forbidden_words: list = []
    allowed_words: list = []
    cta_style: str = ""
    language: str
    voice_id: Optional[str] = None
    is_active: bool

class BrandKitCreate(BaseModel):
    description: str = ""
    value_props: dict = {}
    products: dict = {}
    audience: dict = {}
    style_guidelines: dict = {}
    links: dict = {}

class BrandKitResponse(BaseModel):
    id: str
    influencer_id: str
    description: str
    value_props: dict
    products: dict
    audience: dict
    style_guidelines: dict
    links: dict
