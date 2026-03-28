"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tube_agent.config import get_settings
from tube_agent.api.deps import get_storage
from tube_agent.api.routes import channels, videos, jobs, reports, search

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    storage = get_storage()
    storage.create_tables()
    logger.info("Database tables created/verified")
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    # Configure structured logging
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app = FastAPI(
        title="Tube Agent API",
        description="YouTube Channel Analysis System",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Parse CORS origins from config
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix

    app.include_router(channels.router, prefix=prefix)
    app.include_router(videos.router, prefix=prefix)
    app.include_router(jobs.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
