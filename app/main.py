"""
app/main.py
───────────
FastAPI application entry point. Wires together middlewares, lifespan
events, and API routers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from memory import VectorStore
from app.database import get_db_engine
from app.api.router import router as api_router
from app.limiter import limiter
from app.middleware import AuditLogMiddleware
from app.logging_config import configure_logging
import os

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes long-lived resources (vector store, db connections) on startup.
    """
    configure_logging()
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            sentry_sdk.init(dsn=sentry_dsn, integrations=[FastApiIntegration()],
                           traces_sample_rate=0.1, environment=os.getenv("ENVIRONMENT", "production"))
        except ImportError:
            pass

    logger.info("Initializing vector store...")
    try:
        app.state.vector_store = VectorStore()
    except Exception as exc:
        logger.error(f"Failed to initialize vector store: {exc}")
        app.state.vector_store = None

    logger.info("Initializing database connection...")
    try:
        app.state.db_engine = get_db_engine()
    except Exception as exc:
        logger.warning(f"Failed to initialize db engine (mock mode if needed): {exc}")
        app.state.db_engine = None

    yield

    logger.info("Shutting down application resources...")
    # Any necessary cleanup can be done here.


app = FastAPI(
    title="Financial Research Agent API",
    description="Backend API for managing asynchronous financial research jobs.",
    version="1.0.0",
    lifespan=lifespan,
)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except ImportError:
    pass

# ── Middlewares ────────────────────────────────────────────────────────────
import os

_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
_extra_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
] + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditLogMiddleware)

# ── Rate Limiting Setup ────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routing ────────────────────────────────────────────────────────────────
# ── Root Endpoint ──────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "Autonomous Financial Research Agent API",
        "version": "1.0.0",
        "status": "running"
    }

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

