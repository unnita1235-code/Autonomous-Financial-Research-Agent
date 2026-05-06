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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes long-lived resources (vector store, db connections) on startup.
    """
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

# ── Middlewares ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiting Setup ────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routing ────────────────────────────────────────────────────────────────
app.include_router(api_router)

