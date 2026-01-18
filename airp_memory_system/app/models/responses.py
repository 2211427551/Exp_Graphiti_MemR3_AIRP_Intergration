"""
Response models for AIRP Memory System API.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EpisodeResult(BaseModel):
    """Result model for episode creation."""

    uuid: str = Field(..., description="Episode UUID")
    name: str = Field(..., description="Episode name")
    created_at: datetime = Field(..., description="Creation timestamp")
    entities_count: int = Field(0, description="Number of entities extracted")
    relationships_count: int = Field(0, description="Number of relationships extracted")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted entities")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted relationships")


class EntityResult(BaseModel):
    """Result model for entity retrieval."""

    uuid: str = Field(..., description="Entity UUID")
    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    description: Optional[str] = Field(None, description="Entity description")
    created_at: datetime = Field(..., description="Creation timestamp")
    valid_from: Optional[datetime] = Field(None, description="Valid from timestamp")
    valid_until: Optional[datetime] = Field(None, description="Valid until timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SearchResult(BaseModel):
    """Result model for memory search."""

    query: str = Field(..., description="Original search query")
    total_count: int = Field(..., description="Total number of results")
    search_time: float = Field(..., description="Search time in seconds")
    facts: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant facts")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant entities")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant relationships")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    components: Dict[str, str] = Field(..., description="Component statuses")
