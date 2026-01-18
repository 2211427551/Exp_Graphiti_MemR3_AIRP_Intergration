"""Parser data models for SillyTavern format detection and content classification."""

from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class FormatType(str, Enum):
    """SillyTavern content format types."""
    TEXT = "text"
    INSTRUCTION = "instruction"
    DIALOG_HISTORY = "dialog_history"
    WORLD_INFO = "world_info"
    CHARACTER_INFO = "character_info"
    NARRATIVE = "narrative"


class WorldInfoType(str, Enum):
    """World info entry types."""
    LOCATION = "location"
    CATEGORY = "category"
    FACTION = "faction"
    SCHOOL = "school"
    ORGANIZATION = "organization"
    APPLICATION = "application"
    CONCEPT = "concept"
    CHARACTER = "character"


class ContentCategory(str, Enum):
    """Content classification categories."""
    INSTRUCTIONAL = "instructional"
    NARRATIVE = "narrative"
    MIXED = "mixed"


class ParsedBlock(BaseModel):
    """A parsed content block with format type and metadata."""
    content: str = Field(..., description="The actual text content")
    format_type: FormatType = Field(..., description="Detected format type")
    start_pos: int = Field(..., description="Starting position in original text")
    end_pos: int = Field(..., description="Ending position in original text")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    extracted_entities: Optional[List[str]] = Field(default_factory=list, description="Extracted entity names")


class DetectionResult(BaseModel):
    """Result of format detection on input text."""
    primary_format: FormatType = Field(..., description="Primary detected format")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)
    parsed_blocks: List[ParsedBlock] = Field(default_factory=list, description="Parsed content blocks")
    role_names: Optional[Tuple[str, str]] = Field(default=None, description="Extracted role names (user, assistant)")
    has_chat_history: bool = Field(default=False, description="Whether chat history is present")
    has_world_info: bool = Field(default=False, description="Whether world info is present")


class ClassifiedContent(BaseModel):
    """Result of content classification."""
    instructional_blocks: List[ParsedBlock] = Field(default_factory=list, description="Instructional content blocks")
    narrative_blocks: List[ParsedBlock] = Field(default_factory=list, description="Narrative content blocks")
    role_names: Optional[Tuple[str, str]] = Field(default=None, description="Role names if dialog history")
    has_world_info: bool = Field(default=False, description="Whether world info is present")
    has_dialog_history: bool = Field(default=False, description="Whether dialog history is present")
    confidence_score: float = Field(..., description="Overall classification confidence", ge=0.0, le=1.0)


class WorldInfoEntry(BaseModel):
    """A parsed world info entry."""
    entry_type: WorldInfoType = Field(..., description="Type of world info entry")
    name: str = Field(..., description="Entry name/identifier")
    content: str = Field(..., description="Entry content/description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    hash: Optional[str] = Field(default=None, description="MD5 hash for change detection")


class DialogTurn(BaseModel):
    """A single dialog turn in chat history."""
    role: str = Field(..., description="Speaker role (user/assistant/system)")
    content: str = Field(..., description="Turn content")
    turn_number: int = Field(..., description="Turn index in conversation")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    hash: Optional[str] = Field(default=None, description="Hash for change detection")


class ParseResult(BaseModel):
    """Complete parsing result for input content."""
    detection_result: DetectionResult = Field(..., description="Format detection results")
    classification_result: Optional[ClassifiedContent] = Field(default=None, description="Content classification results")
    world_info_entries: List[WorldInfoEntry] = Field(default_factory=list, description="Parsed world info entries")
    dialog_history: List[DialogTurn] = Field(default_factory=list, description="Parsed dialog history")
    parsing_time_ms: float = Field(..., description="Total parsing time in milliseconds")
