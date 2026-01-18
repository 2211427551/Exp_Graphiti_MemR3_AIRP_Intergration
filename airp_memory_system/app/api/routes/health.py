"""
Health check endpoints.
"""
import asyncio
from typing import Dict, Any, Tuple

from fastapi import APIRouter
from pydantic import BaseModel
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis
from openai import OpenAI

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    app_name: str
    version: str
    components: Dict[str, str]


async def check_neo4j() -> Tuple[str, str]:
    """Check Neo4j connectivity.

    Returns:
        (status, detail) tuple
    """
    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run("RETURN 1 AS num")
            record = await result.single()

        await driver.close()
        return ("healthy", "Connected to Neo4j")

    except Exception as e:
        logger.error("Neo4j health check failed", extra={"error": str(e)})
        return ("unhealthy", f"Neo4j connection failed: {str(e)}")


async def check_redis() -> Tuple[str, str]:
    """Check Redis connectivity.

    Returns:
        (status, detail) tuple
    """
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            socket_connect_timeout=2
        )

        await redis_client.ping()
        await redis_client.close()
        return ("healthy", "Connected to Redis")

    except Exception as e:
        logger.error("Redis health check failed", extra={"error": str(e)})
        return ("unhealthy", f"Redis connection failed: {str(e)}")


async def check_deepseek() -> Tuple[str, str]:
    """Check DeepSeek API connectivity.

    Returns:
        (status, detail) tuple
    """
    try:
        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=5
        )

        # Simple test request
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )

        return ("healthy", "DeepSeek API accessible")

    except Exception as e:
        logger.error("DeepSeek health check failed", extra={"error": str(e)})
        return ("unhealthy", f"DeepSeek API connection failed: {str(e)}")


async def check_siliconflow() -> Tuple[str, str]:
    """Check SiliconFlow API connectivity.

    Returns:
        (status, detail) tuple
    """
    try:
        client = OpenAI(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            timeout=5
        )

        # Simple test request
        response = client.embeddings.create(
            model=settings.siliconflow_embedding_model,
            input="test"
        )

        return ("healthy", "SiliconFlow API accessible")

    except Exception as e:
        logger.error("SiliconFlow health check failed", extra={"error": str(e)})
        return ("unhealthy", f"SiliconFlow API connection failed: {str(e)}")


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status of application and its components

    Note:
        Health checks run in parallel for better performance
    """
    # Run all health checks in parallel
    results = await asyncio.gather(
        check_neo4j(),
        check_redis(),
        check_deepseek(),
        check_siliconflow(),
        return_exceptions=True
    )

    neo4j_status, neo4j_detail = results[0] if not isinstance(results[0], Exception) else ("unhealthy", str(results[0]))
    redis_status, redis_detail = results[1] if not isinstance(results[1], Exception) else ("unhealthy", str(results[1]))
    deepseek_status, deepseek_detail = results[2] if not isinstance(results[2], Exception) else ("unhealthy", str(results[2]))
    siliconflow_status, siliconflow_detail = results[3] if not isinstance(results[3], Exception) else ("unhealthy", str(results[3]))

    # Determine overall status
    all_healthy = all([
        neo4j_status == "healthy",
        redis_status == "healthy",
        deepseek_status == "healthy",
        siliconflow_status == "healthy"
    ])

    overall_status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        version=settings.app_version,
        components={
            "api": "healthy",
            "neo4j": neo4j_status,
            "redis": redis_status,
            "deepseek": deepseek_status,
            "siliconflow": siliconflow_status,
        }
    )


@router.get("/live")
async def liveness():
    """Liveness probe - returns 200 if service is running."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """Readiness probe - returns 200 if service is ready to handle requests."""
    # TODO: Check critical dependencies
    return {"status": "ready"}
