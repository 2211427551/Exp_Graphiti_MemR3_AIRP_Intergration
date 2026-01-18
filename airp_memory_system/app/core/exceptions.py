"""
Custom exception classes for AIRP Memory System.
"""
from typing import Optional, Dict, Any, List


class AIRPMemoryError(Exception):
    """Base exception for AIRP Memory System."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class GraphitiConnectionError(AIRPMemoryError):
    """Exception raised when Neo4j/Graphiti connection fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, details)


class ValidationError(AIRPMemoryError):
    """Exception raised when input validation fails."""

    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, Any]] = None
    ):
        """Initialize exception.

        Args:
            message: Error message
            validation_errors: Detailed validation errors
        """
        self.validation_errors = validation_errors or {}
        super().__init__(message, {"validation_errors": self.validation_errors})


class EpisodeError(AIRPMemoryError):
    """Exception raised when episode operations fail."""

    def __init__(self, message: str, episode_id: Optional[str] = None):
        """Initialize exception.

        Args:
            message: Error message
            episode_id: Episode UUID if available
        """
        details = {"episode_id": episode_id} if episode_id else {}
        super().__init__(message, details)


class SearchError(AIRPMemoryError):
    """Exception raised when search operations fail."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ):
        """Initialize exception.

        Args:
            message: Error message
            query: Search query if available
            filters: Search filters if available
        """
        details = {}
        if query:
            details["query"] = query
        if filters:
            details["filters"] = filters
        super().__init__(message, details)


class LLMError(AIRPMemoryError):
    """Exception raised when LLM API calls fail."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize exception.

        Args:
            message: Error message
            provider: LLM provider (deepseek, siliconflow)
            model: Model name
        """
        details = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        super().__init__(message, details)


class EmbeddingError(LLMError):
    """Exception raised when embedding operations fail."""
    pass


class RerankerError(LLMError):
    """Exception raised when reranking operations fail."""
    pass


class ParserError(AIRPMemoryError):
    """Base exception for parser errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, details)


class UnsupportedFormatError(ParserError):
    """Exception raised when input format is not supported."""

    def __init__(self, format_type: str, supported_formats: List[str]):
        """Initialize exception.

        Args:
            format_type: Unsupported format type
            supported_formats: List of supported format types
        """
        message = f"Unsupported format: {format_type}. Supported formats: {', '.join(supported_formats)}"
        details = {"format_type": format_type, "supported_formats": supported_formats}
        super().__init__(message, details)


class ParsingError(ParserError):
    """Exception raised when parsing fails."""

    def __init__(self, message: str, content_preview: Optional[str] = None):
        """Initialize exception.

        Args:
            message: Error message
            content_preview: Preview of content that failed to parse
        """
        details = {"content_preview": content_preview[:100] if content_preview else None}
        super().__init__(message, details)


class ClassificationError(ParserError):
    """Exception raised when content classification fails."""

    def __init__(self, message: str, confidence_score: Optional[float] = None):
        """Initialize exception.

        Args:
            message: Error message
            confidence_score: Confidence score when classification failed
        """
        details = {"confidence_score": confidence_score}
        super().__init__(message, details)
