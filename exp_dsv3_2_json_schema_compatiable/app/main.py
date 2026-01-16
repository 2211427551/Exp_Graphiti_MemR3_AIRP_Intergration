"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
from app.api.routes import chat, health
from app.middleware.logging_middleware import LoggingMiddleware
from app.utils.exceptions import DeepSeekAPIError

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Args:
        app: FastAPI application instance
    """
    logger.info(
        "Starting application",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
        }
    )
    yield
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DeepSeek V3.2 JSON Schema Compatible API with Strict Mode Support",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


# Exception handlers
@app.exception_handler(DeepSeekAPIError)
async def deepseek_api_error_handler(request, exc: DeepSeekAPIError):
    """Handle DeepSeek API errors.

    Args:
        request: Request that caused the error
        exc: Exception instance

    Returns:
        JSON response with error details
    """
    logger.error(
        "DeepSeek API error",
        extra={
            "error": str(exc),
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=502,
        content={"error": "deepseek_api_error", "message": str(exc)}
    )


# Include routers
app.include_router(health.router)
app.include_router(chat.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
