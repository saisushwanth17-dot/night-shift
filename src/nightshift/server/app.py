"""FastAPI Application for Night Shift."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nightshift import __version__
from nightshift.config import settings
from nightshift.memory.store import EngineeringMemoryStore
from nightshift.server.routes import (
    briefing_router,
    health_router,
    triggers_router,
    webhooks_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan setup: ensure database tables exist."""
    # Ensure SQLite tables exist
    EngineeringMemoryStore(settings.db_path)
    yield


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="Night Shift API",
        description="Autonomous Software Maintenance Agent Service",
        version=__version__,
        lifespan=lifespan,
    )

    # Enable CORS for Next.js / frontend UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(health_router)
    app.include_router(webhooks_router)
    app.include_router(triggers_router)
    app.include_router(briefing_router)

    return app


app = create_app()
