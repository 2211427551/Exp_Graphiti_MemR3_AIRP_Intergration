"""
API路由模块
"""

from .health import router as health_router
from .episodes import router as episodes_router
from .search import router as search_router

__all__ = [
    'health_router',
    'episodes_router',
    'search_router'
]
