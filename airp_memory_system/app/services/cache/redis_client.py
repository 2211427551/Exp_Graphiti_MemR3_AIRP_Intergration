"""
Redis cache client for AIRP Memory System.
"""
from typing import Optional, Any
import json

import redis
from redis.asyncio import Redis as AsyncRedis

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class RedisClient:
    """
    Redis client wrapper for caching.

    Provides:
    - Search result caching
    - Embedding caching
    - Session storage

    TODO: Full implementation in Week 8
    """

    def __init__(self):
        """Initialize Redis client."""
        self.client: Optional[AsyncRedis] = None
        logger.info("Redis client initialized")

    async def connect(self) -> None:
        """
        Establish Redis connection.

        Raises:
            Exception: If connection fails
        """
        try:
            self.client = AsyncRedis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
                max_connections=settings.redis_max_connections,
            )

            # Test connection
            await self.client.ping()
            logger.info("Redis connection established")

        except Exception as e:
            logger.error("Redis connection failed", extra={"error": str(e)})
            raise

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.client:
            return None

        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        if not self.client:
            return

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await self.client.set(key, value, ex=ttl or settings.redis_cache_ttl)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if self.client:
            await self.client.delete(key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")


# Global client instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """
    Get or create Redis client singleton.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()

    return _redis_client
