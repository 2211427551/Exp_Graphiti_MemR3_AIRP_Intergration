"""Change detection data models."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class HashAlgorithm(str, Enum):
    """Supported hash algorithms."""
    MD5 = "md5"
    XXHASH = "xxhash"
    SHA256 = "sha256"


class ChangeType(str, Enum):
    """Types of changes detected."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class EntryChange(BaseModel):
    """Change detected for a single entry."""
    change_type: ChangeType = Field(..., description="Type of change")
    entry_type: str = Field(..., description="Type of entry (world_info/dialog)")
    identifier: str = Field(..., description="Entry identifier (name/turn_number)")
    old_hash: Optional[str] = Field(default=None, description="Previous hash value")
    new_hash: Optional[str] = Field(default=None, description="New hash value")
    old_value: Optional[Dict[str, Any]] = Field(default=None, description="Previous entry data")
    new_value: Optional[Dict[str, Any]] = Field(default=None, description="New entry data")
    entry_type_field: Optional[str] = Field(default=None, description="WorldInfoType if applicable")
    name: Optional[str] = Field(default=None, description="Entry name if applicable")
    role: Optional[str] = Field(default=None, description="Dialog role if applicable")
    turn_number: Optional[int] = Field(default=None, description="Turn number if applicable")
    content: Optional[str] = Field(default=None, description="Content if applicable")


class ChangeReport(BaseModel):
    """Complete change detection report."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When changes were detected")
    total_entries_before: int = Field(..., description="Total entries before changes")
    total_entries_after: int = Field(..., description="Total entries after changes")
    added_count: int = Field(default=0, description="Number of added entries")
    removed_count: int = Field(default=0, description="Number of removed entries")
    modified_count: int = Field(default=0, description="Number of modified entries")
    unchanged_count: int = Field(default=0, description="Number of unchanged entries")
    changes: List[EntryChange] = Field(default_factory=list, description="List of all changes")
    detection_time_ms: float = Field(..., description="Time taken for change detection in ms")
    hash_algorithm: HashAlgorithm = Field(..., description="Hash algorithm used")


class DialogDiff(BaseModel):
    """Dialog history difference report."""
    structural_changes: bool = Field(..., description="Whether structural changes occurred")
    turn_count_changed: bool = Field(default=False, description="Whether turn count changed")
    role_sequence_changed: bool = Field(default=False, description="Whether role sequence changed")
    content_changes: List[EntryChange] = Field(default_factory=list, description="Content changes per turn")
    before_summary: Dict[str, int] = Field(default_factory=dict, description="Summary before (turns per role)")
    after_summary: Dict[str, int] = Field(default_factory=dict, description="Summary after (turns per role)")


class HashComputationStats(BaseModel):
    """Statistics for hash computation."""
    total_hashes_computed: int = Field(..., description="Total hashes computed")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    computation_time_ms: float = Field(..., description="Total computation time in ms")
    algorithm_used: HashAlgorithm = Field(..., description="Hash algorithm used")
