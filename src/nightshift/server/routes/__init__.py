"""Server routes package for Night Shift."""

from nightshift.server.routes.briefing import router as briefing_router
from nightshift.server.routes.health import router as health_router
from nightshift.server.routes.triggers import router as triggers_router
from nightshift.server.routes.webhooks import router as webhooks_router

__all__ = [
    "briefing_router",
    "health_router",
    "triggers_router",
    "webhooks_router",
]
