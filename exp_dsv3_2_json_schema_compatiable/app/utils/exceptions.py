"""
Custom exception classes for the application.
"""
from typing import List, Optional


class DeepSeekAPIError(Exception):
    """Base exception for DeepSeek API errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DeepSeekRateLimitError(DeepSeekAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class DeepSeekTimeoutError(DeepSeekAPIError):
    """Exception raised when request times out."""

    pass


class DeepSeekValidationError(DeepSeekAPIError):
    """Exception raised when JSON Schema validation fails."""

    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class DeepSeekSchemaTransformError(DeepSeekAPIError):
    """Exception raised when schema transformation fails."""

    pass
