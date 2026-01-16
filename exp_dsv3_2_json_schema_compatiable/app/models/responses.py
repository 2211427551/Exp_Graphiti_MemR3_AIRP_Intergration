"""
Response models for API endpoints using Pydantic for validation.
"""
from typing import List, Optional

from pydantic import BaseModel


class ToolCallFunction(BaseModel):
    """Tool call function model."""

    name: str
    arguments: str


class ToolCall(BaseModel):
    """Tool call model in response."""

    id: str
    type: str
    function: ToolCallFunction


class ResponseMessage(BaseModel):
    """Response message model."""

    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class Choice(BaseModel):
    """Choice model in response."""

    index: int
    message: ResponseMessage
    finish_reason: str


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat completion response model."""

    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str
