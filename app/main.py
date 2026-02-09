"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging, get_logger
from app.middleware.logging_middleware import LoggingMiddleware
from app.routes import (
    health,
    auth,
    users,
    albums,
    reviews,
    diary,
    lists,
    explore,
    ai,
    search,
    notifications,
    integrations,
)


logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting %s", settings.app_name)
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(albums.router, prefix=settings.api_v1_prefix)
app.include_router(reviews.router, prefix=settings.api_v1_prefix)
app.include_router(diary.router, prefix=settings.api_v1_prefix)
app.include_router(lists.router, prefix=settings.api_v1_prefix)
app.include_router(explore.router, prefix=settings.api_v1_prefix)
app.include_router(ai.router, prefix=settings.api_v1_prefix)
app.include_router(search.router, prefix=settings.api_v1_prefix)
app.include_router(notifications.router, prefix=settings.api_v1_prefix)
app.include_router(integrations.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Listenr API", "docs": "/docs"}
