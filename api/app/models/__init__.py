# Import all models so SQLModel.metadata sees them
from app.models.user import User, OrgMember  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.cost_center import CostCenter  # noqa: F401
from app.models.influencer import Influencer, BrandKit, InfluencerAsset  # noqa: F401
from app.models.content import MacroContent, ContentItem, Approval  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.social import SocialAccount  # noqa: F401
from app.models.tracking import TrackingLink, Event, Lead  # noqa: F401
from app.models.metrics import MetricsDaily  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.agent import AgentSession, AgentMessage, AgentAction  # noqa: F401
from app.models.market import (  # noqa: F401
    MarketSource,
    Competitor,
    MarketFinding,
    MarketBrief,
    ContentBrief,
)
from app.models.embedding import BrandKitEmbedding  # noqa: F401
from app.models.template import ContentTemplate  # noqa: F401
from app.models.usage import UsageLog  # noqa: F401
from app.models.webhook import WebhookConfig  # noqa: F401
