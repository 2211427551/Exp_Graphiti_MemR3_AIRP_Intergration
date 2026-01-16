"""
Request models for API endpoints using Pydantic for validation.
"""
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message model."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ToolFunction(BaseModel):
    """Tool function definition model."""

    name: str = Field(..., min_length=1, max_length=64)
    description: str
    strict: bool = True
    parameters: Dict[str, Any]


class Tool(BaseModel):
    """Tool definition model for function calling."""

    type: Literal["function"] = "function"
    function: ToolFunction


class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""

    model: Literal["deepseek-chat", "deepseek-reasoner"]
    messages: List[Message] = Field(..., min_length=1)
    tools: Optional[List[Tool]] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: bool = False
