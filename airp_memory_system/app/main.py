"""
FastAPI application entry point for AIRP Memory System.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
from app.api.routes import health, memory, chat
from app.middleware.tracking import TrackingMiddleware
from app.core.exceptions import (
    AIRPMemoryError,
    GraphitiConnectionError,
    ValidationError,
)

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info(
        "Starting AIRP Memory System",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
            "neo4j_uri": settings.neo4j_uri,
            "deepseek_model": settings.deepseek_model,
        }
    )

    # Initialize Neo4j connection and Graphiti
    try:
        from app.services.memory.graphiti_client import get_graphiti_client
        graphiti_client = await get_graphiti_client()
        logger.info("Graphiti client initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Graphiti", extra={"error": str(e)})
        # Continue startup even if Graphiti fails
        # Health checks will report the issue

    yield

    # Shutdown
    logger.info("Shutting down AIRP Memory System")

    # Close Neo4j connection
    try:
        from app.services.memory.graphiti_client import get_graphiti_client
        graphiti_client = await get_graphiti_client()
        await graphiti_client.close()
        logger.info("Graphiti client closed")
    except Exception as e:
        logger.error("Error closing Graphiti client", extra={"error": str(e)})


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Role Play Memory System using Graphiti Temporal Knowledge Graph",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add tracking middleware
app.add_middleware(TrackingMiddleware)


# Exception handlers
@app.exception_handler(GraphitiConnectionError)
async def graphiti_connection_error_handler(request, exc: GraphitiConnectionError):
    """Handle Graphiti connection errors.

    Args:
        request: Request that caused the error
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    logger.error(
        "Graphiti connection error",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": "graphiti_connection_error",
            "message": "Failed to connect to Neo4j database",
            "details": str(exc)
        }
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Handle validation errors.

    Args:
        request: Request that caused the error
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    logger.warning(
        "Validation error",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": str(exc),
            "details": exc.validation_errors
        }
    )


@app.exception_handler(AIRPMemoryError)
async def airp_memory_error_handler(request, exc: AIRPMemoryError):
    """Handle general AIRP memory errors.

    Args:
        request: Request that caused the error
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    logger.error(
        "AIRP memory error",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "airp_memory_error",
            "message": str(exc)
        }
    )


# Include routers
app.include_router(health.router)
app.include_router(memory.router)
app.include_router(chat.router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "AIRP Memory System - Temporal Knowledge Graph for AI Role Play",
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1
    )
