"""
Internal schemas for AIRP Memory System.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


# Graphiti-related schemas
class GraphitiEpisode(BaseModel):
    """Schema for Graphiti episode."""

    name: str
    episode_body: str
    source: str
    reference_time: Optional[datetime] = None
    group_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GraphitiEntity(BaseModel):
    """Schema for Graphiti entity."""

    uuid: str
    name: str
    entity_type: str
    description: Optional[str] = None
    created_at: datetime
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class GraphitiRelationship(BaseModel):
    """Schema for Graphiti relationship."""

    uuid: str
    source_entity_uuid: str
    target_entity_uuid: str
    relationship_type: str
    attributes: Optional[Dict[str, Any]] = None
    created_at: datetime
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
