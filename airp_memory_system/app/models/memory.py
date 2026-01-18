"""Memory-related data models for Week 5.

This module defines core models for entity management, search, and deduplication.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime


class SearchStrategy(str, Enum):
    """Search strategy types for memory retrieval.

    VECTOR: Semantic vector search using embeddings
    KEYWORD: Text-based keyword matching
    GRAPH_TRAVERSAL: Graph relationship-based exploration
    HYBRID: Combination of multiple strategies with weighted scoring
    """
    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH_TRAVERSAL = "graph"
    HYBRID = "hybrid"


class Entity(BaseModel):
    """Represents an entity in the knowledge graph.

    Entities are the fundamental nodes in the graph representing
    people, places, things, concepts, etc.
    """
    uuid: str = Field(..., description="Unique identifier for the entity")
    name: str = Field(..., description="Entity name")
    entity_type: Optional[str] = Field(
        default=None,
        description="Entity type (e.g., person, location, organization)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed entity description"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when entity was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when entity was last updated"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata as key-value pairs"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Relationship(BaseModel):
    """Represents a relationship between two entities.

    Relationships are directed edges in the knowledge graph that
    connect entities and describe how they relate to each other.
    """
    uuid: str = Field(..., description="Unique identifier for the relationship")
    source_uuid: str = Field(..., description="UUID of the source entity")
    target_uuid: str = Field(..., description="UUID of the target entity")
    relationship_type: str = Field(
        ...,
        description="Type of relationship (e.g., LOCATED_IN, KNOWS, PART_OF)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed relationship description"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when relationship was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata as key-value pairs"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchResult(BaseModel):
    """Search result from memory retrieval.

    Represents a single result from a search operation, including
    relevance scoring and metadata.
    """
    uuid: str = Field(..., description="Unique identifier for the result")
    content: str = Field(..., description="Result content (episode or entity description)")
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score (0-1, higher is more relevant)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the result"
    )
    entity_uuids: List[str] = Field(
        default_factory=list,
        description="UUIDs of related entities (if applicable)"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeduplicationResult(BaseModel):
    """Result of a deduplication check.

    Indicates whether an item (entity or episode) is a duplicate
    of existing content and provides similarity information.
    """
    is_duplicate: bool = Field(
        ...,
        description="Whether the item is a duplicate"
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1, higher is more similar)"
    )
    matched_uuid: Optional[str] = Field(
        default=None,
        description="UUID of the matched item if duplicate"
    )
    match_reason: str = Field(
        ...,
        description="Explanation of why this was/wasn't a match"
    )


class EpisodeSummary(BaseModel):
    """Summary of an episode in memory.

    Provides high-level information about an episode including
    extracted entities and relationships.
    """
    episode_uuid: str = Field(..., description="Unique identifier for the episode")
    name: str = Field(..., description="Episode name/title")
    content_summary: str = Field(..., description="Brief summary of episode content")
    entity_count: int = Field(
        default=0,
        ge=0,
        description="Number of entities extracted from episode"
    )
    relationship_count: int = Field(
        default=0,
        ge=0,
        description="Number of relationships found in episode"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when episode was created"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MergeSuggestion(BaseModel):
    """Suggestion for merging duplicate entities.

    Provides information about potentially duplicate entities
    and recommendations for merging them.
    """
    entity_uuids: List[str] = Field(
        ...,
        description="UUIDs of entities that should be merged"
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average similarity among suggested entities"
    )
    reason: str = Field(..., description="Explanation of why merge is suggested")
    recommended_name: str = Field(
        ...,
        description="Suggested name for merged entity"
    )
    recommended_description: str = Field(
        ...,
        description="Suggested description for merged entity"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the merge suggestion"
    )
