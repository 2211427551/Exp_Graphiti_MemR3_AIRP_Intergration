"""
Dependency injection for API routes.
"""
from fastapi import Depends

from app.services.memory.graphiti_client import get_graphiti_client
from app.services.llm.deepseek_client import DeepSeekClient
from app.services.llm.embedding_client import EmbeddingClient
from app.services.cache.redis_client import get_redis_client
from app.core.config import settings


def get_deepseek_client():
    """Dependency to get DeepSeek client instance."""
    return DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.deepseek_timeout,
        max_retries=settings.deepseek_max_retries
    )


def get_embedding_client():
    """Dependency to get Embedding client instance."""
    return EmbeddingClient(
        api_key=settings.siliconflow_api_key,
        base_url=settings.siliconflow_base_url,
        model=settings.siliconflow_embedding_model
    )


# Export all dependencies
__all__ = [
    "get_graphiti_client",
    "get_deepseek_client",
    "get_embedding_client",
    "get_redis_client",
]
