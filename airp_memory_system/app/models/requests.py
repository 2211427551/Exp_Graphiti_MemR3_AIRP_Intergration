"""
Request models for AIRP Memory System API.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.memory import SearchStrategy


class EpisodeInput(BaseModel):
    """Input model for creating episodes."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "User Conversation 001",
                "episode_body": "Alice works as a software engineer at TechCorp.",
                "source": "text",
                "source_description": "Customer interaction",
                "reference_time": "2025-01-16T12:00:00Z",
                "group_id": "customer_interactions",
            }
        }
    )

    name: str = Field(..., description="Episode name")
    episode_body: str = Field(..., description="Episode content")
    source: str = Field(..., description="Source type (text, json, etc.)")
    source_description: Optional[str] = Field(None, description="Source description")
    reference_time: Optional[datetime] = Field(None, description="Reference timestamp")
    group_id: Optional[str] = Field(None, description="Group ID for related episodes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SearchRequest(BaseModel):
    """Input model for searching memory."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What do we know about Alice?",
                "num_results": 10,
                "strategy": "hybrid",
                "filters": {
                    "entity_types": ["Person", "Organization"]
                }
            }
        }
    )

    query: str = Field(..., description="Search query")
    num_results: int = Field(10, ge=1, le=100, description="Number of results")
    strategy: Optional[SearchStrategy] = Field(
        default=SearchStrategy.HYBRID,
        description="Search strategy (vector, keyword, graph, hybrid)"
    )
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
