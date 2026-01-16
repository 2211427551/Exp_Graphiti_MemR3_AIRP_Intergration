"""
Security utilities for API authentication.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# API Key header security scheme
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> bool:
    """Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        True if API key is valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # For now, we accept any non-empty API key
    # In production, you should validate against a database or secure store
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Please provide X-API-Key header.",
        )

    # Add your API key validation logic here
    # Example: if api_key not in VALID_API_KEYS:
    #     raise HTTPException(status_code=401, detail="Invalid API key")

    return True
