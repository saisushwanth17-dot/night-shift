"""Health check routes."""

from fastapi import APIRouter
from nightshift import __version__
from nightshift.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
async def health_check():
    """Health check endpoint providing service runtime information."""
    return {
        "status": "healthy",
        "service": "nightshift",
        "version": __version__,
        "sandbox_mode": settings.sandbox_mode.value,
        "database": str(settings.db_path),
    }
