from contextlib import asynccontextmanager
from time import time
from collections import defaultdict
import logging
import json as _json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings


# --- Structured JSON Logging ---
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "method"):
            log["method"] = record.method  # type: ignore
        if hasattr(record, "path"):
            log["path"] = record.path  # type: ignore
        if hasattr(record, "status_code"):
            log["status_code"] = record.status_code  # type: ignore
        if hasattr(record, "duration_ms"):
            log["duration_ms"] = record.duration_ms  # type: ignore
        return _json.dumps(log, ensure_ascii=False)


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    handler = logging.StreamHandler()
    if settings.APP_ENV != "local":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.handlers = [handler]


setup_logging()
logger = logging.getLogger(__name__)

# --- Rate Limiter ---
# Global default: 100 requests/minute per IP
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
)


# --- Path-based rate limit storage (in-memory sliding window) ---
_path_rate_buckets: dict[str, list[float]] = defaultdict(list)

# Stricter limits by path prefix: (max_requests, window_seconds)
_PATH_LIMITS: dict[str, tuple[int, int]] = {
    "/auth/login": (10, 60),      # 10 req/min — brute force protection
    "/auth/register": (10, 60),   # 10 req/min — brute force protection
    "/agent/": (20, 60),          # 20 req/min — AI endpoints
}


def _check_path_limit(ip: str, path: str) -> bool:
    """Return True if request should be blocked (limit exceeded)."""
    for prefix, (max_reqs, window) in _PATH_LIMITS.items():
        if path.startswith(prefix):
            key = f"{prefix}:{ip}"
            now = time()
            bucket = _path_rate_buckets[key]
            # Remove expired entries
            cutoff = now - window
            _path_rate_buckets[key] = [t for t in bucket if t > cutoff]
            bucket = _path_rate_buckets[key]
            if len(bucket) >= max_reqs:
                return True
            bucket.append(now)
            return False
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema managed by Alembic migrations (alembic upgrade head)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Attach limiter to app state (required by slowapi)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


# Custom 429 handler — pt-BR (slowapi global limit)
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Limite de requisições excedido. Tente novamente em alguns instantes.",
        },
    )


# Path-based rate limiting middleware (auth & agent stricter limits)
@app.middleware("http")
async def path_rate_limit_middleware(request: Request, call_next):
    ip = get_remote_address(request)
    if _check_path_limit(ip, request.url.path):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Limite de requisições excedido. Tente novamente em alguns instantes.",
            },
        )
    response = await call_next(request)
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time()
    response = await call_next(request)
    duration = round((time() - start) * 1000, 1)
    if request.url.path != "/health":
        logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration,
            },
        )
    return response


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
