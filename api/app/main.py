from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema managed by Alembic migrations (alembic upgrade head)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# --- Register routers ---
from app.routers import (  # noqa: E402
    auth,
    organizations,
    cost_centers,
    influencers,
    macro_contents,
    content_items,
    campaigns,
    social,
    tracking,
    leads,
    metrics,
    agent_marketing,
    agent_market,
    audit,
    notifications,
    templates,
    webhooks,
    usage,
)
from app.routers import invites, admin, billing  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(organizations.router, prefix="/orgs", tags=["Organizations"])
app.include_router(cost_centers.router, prefix="/cost-centers", tags=["Cost Centers"])
app.include_router(influencers.router, prefix="/influencers", tags=["Influencers"])
app.include_router(macro_contents.router, prefix="/macro-contents", tags=["Macro Content"])
app.include_router(content_items.router, prefix="/content-items", tags=["Content Items"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
app.include_router(social.router, prefix="/integrations", tags=["Social Integrations"])
app.include_router(tracking.router, prefix="/tracking", tags=["Tracking"])
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
app.include_router(agent_marketing.router, prefix="/agent/marketing", tags=["Marketing Agent"])
app.include_router(agent_market.router, prefix="/agent/market", tags=["Market Agent"])
app.include_router(audit.router, prefix="/audit-logs", tags=["Audit"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(templates.router, prefix="/templates", tags=["Templates"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(usage.router, prefix="/usage", tags=["Usage & Billing"])
app.include_router(invites.router, prefix="/invite", tags=["Invites"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(billing.router, prefix="/billing", tags=["Billing"])
