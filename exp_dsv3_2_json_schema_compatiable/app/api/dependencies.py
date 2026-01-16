"""
API dependencies and dependency injection.
"""
from fastapi import Depends

from app.services.deepseek_client import DeepSeekClient
from app.core.config import settings


def get_deepseek_client() -> DeepSeekClient:
    """Get a DeepSeek client instance.

    Returns:
        Configured DeepSeek client
    """
    return DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.deepseek_timeout,
        max_retries=settings.deepseek_max_retries
    )
