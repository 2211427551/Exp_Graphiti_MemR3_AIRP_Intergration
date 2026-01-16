"""
JSON Schema definition models.
"""
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class JSONSchemaProperty(BaseModel):
    """JSON Schema property definition."""

    type: str
    description: Optional[str] = None
    # String-specific
    pattern: Optional[str] = None
    format: Optional[str] = None
    # Number-specific
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    enum: Optional[List[Any]] = None
    # Array-specific
    items: Optional["JSONSchemaProperty"] = None
    # Object-specific
    properties: Optional[Dict[str, "JSONSchemaProperty"]] = None


class JSONSchema(BaseModel):
    """JSON Schema model for validation."""

    type: str = "object"
    properties: Dict[str, JSONSchemaProperty] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = False
    # Allow anyOf for complex schemas
    anyOf: Optional[List[Dict[str, Any]]] = None
