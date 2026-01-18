"""
Logging configuration using structlog for structured logging.
Based on exp_dsv3_2_json_schema_compatiable pattern.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application-specific context to log entries.

    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with app context
    """
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request ID to log entries if present in context.

    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with request ID
    """
    if "request_id" in event_dict:
        event_dict["request_id"] = event_dict.pop("request_id")
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Configure structlog processors
    processors: list[Processor] = [
        # Add context from contextvars
        structlog.contextvars.merge_contextvars,

        # Add standard logging attributes
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,

        # Add application context
        add_app_context,
        add_request_id,

        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # Add call stack info for debugging
        structlog.processors.StackInfoRenderer(),

        # Format exceptions
        structlog.processors.format_exc_info,

        # Add caller information
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
    ]

    # Choose output format
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback
            )
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured bound logger
    """
    return structlog.get_logger(name)


def bind_request_id(request_id: str) -> None:
    """Bind request ID to logging context.

    Args:
        request_id: Request ID to bind
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)


def clear_request_id() -> None:
    """Clear request ID from logging context."""
    structlog.contextvars.unbind_contextvars("request_id")
