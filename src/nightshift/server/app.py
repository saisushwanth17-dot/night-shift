"""FastAPI Application for Night Shift."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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
    EngineeringMemoryStore(settings.db_path)
    yield


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="Night Shift API & Operations Console",
        description="Autonomous Software Maintenance Agent Service",
        version=__version__,
        lifespan=lifespan,
    )

    # Enable CORS
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

    # Serve Operations Console Dashboard
    template_path = Path(__file__).parent / "templates" / "dashboard.html"

    @app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
    @app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
    async def get_dashboard():
        """Serve the interactive Night Shift Operations Console UI."""
        if template_path.exists():
            return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Night Shift Operations Console</h1>", status_code=200)

    return app


app = create_app()
