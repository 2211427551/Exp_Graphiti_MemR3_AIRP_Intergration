"""
Request tracking middleware.
Based on exp_dsv3_2_json_schema_compatiable pattern.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import get_logger, bind_request_id, clear_request_id

logger = get_logger(__name__)


class TrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking requests and adding request IDs.

    Features:
    - Generates unique request ID
    - Logs request details
    - Measures response time
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and add tracking.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response with tracking headers
        """
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Bind request ID to logging context
        bind_request_id(request_id)

        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            "Incoming request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        finally:
            # Clear request ID from context
            clear_request_id()
