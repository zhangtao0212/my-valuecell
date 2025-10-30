"""API router module."""

from .agent import create_agent_router
from .i18n import create_i18n_router, get_i18n_router
from .system import create_system_router

__all__ = [
    "create_i18n_router",
    "get_i18n_router",
    "create_system_router",
    "create_agent_router",
]
