"""
变化检测数据模型

定义世界书和对话历史状态跟踪所需的数据结构
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """来源引用"""
    source_type: str = Field(..., description="来源类型")
    source_id: str = Field(..., description="来源ID")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")


class WorldInfoEntry(BaseModel):
    """世界书条目"""
    
    # 核心属性
    entry_id: str = Field(..., description="唯一标识（基于内容哈希）")
    entry_type: str = Field(..., description="类型：location, character, concept等")
    name: str = Field(..., description="条目名称")
    content: str = Field(..., description="条目内容")
    content_hash: str = Field(..., description="内容哈希（用于快速比对）")
    properties: Dict[str, Any] = Field(default_factory=dict, description="属性")
    
    # 时间属性
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    
    # 来源追踪
    source: str = Field(..., description="来源（world_info标签等）")
    session_id: str = Field(..., description="所属会话")
    
    # 版本控制
    version: int = Field(default=0, description="版本号")
    
    # 状态
    status: str = Field(default="active", description="状态：active, deleted, superseded, expired")
    status_reason: Optional[str] = Field(None, description="状态原因")


class WorldInfoState(BaseModel):
    """世界书状态跟踪器"""
    
    entries: Dict[str, WorldInfoEntry] = Field(
        default_factory=dict,
        description="entry_id -> entry映射"
    )
    entry_hashes: Dict[str, str] = Field(
        default_factory=dict,
        description="content_hash -> entry_id映射"
    )
    timestamp: Optional[datetime] = Field(None, description="时间戳")
    version: int = Field(default=0, description="状态版本")


class ChatMessage(BaseModel):
    """对话消息"""
    
    message_id: str = Field(..., description="消息ID")
    role: str = Field(..., description="User或Assistant")
    content: str = Field(..., description="消息内容")
    content_hash: str = Field(..., description="内容哈希")
    timestamp: Optional[datetime] = Field(None, description="时间戳")
    turn_number: int = Field(..., description="轮次编号")
    session_id: str = Field(..., description="会话ID")
    
    # 元数据
    speaker_mapping: Optional[str] = Field(None, description="原始说话者标识（如'Haruki'）")


class ChatHistoryState(BaseModel):
    """对话历史状态跟踪器"""
    
    messages: List[ChatMessage] = Field(
        default_factory=list,
        description="消息列表"
    )
    message_hashes: List[str] = Field(
        default_factory=list,
        description="消息哈希列表"
    )
    total_hash: Optional[str] = Field(None, description="总哈希")
    version: int = Field(default=0, description="版本号")


class StateDiff(BaseModel):
    """状态差异"""
    
    name_changed: bool = Field(default=False)
    content_changed: bool = Field(default=False)
    properties_changed: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    change_type: Optional[str] = Field(None, description="update, expansion, reduction, replacement")
    change_percentage: float = Field(default=0.0, description="变化百分比")


class EntryDifference(BaseModel):
    """条目差异详情"""
    
    entry_id: str
    old: WorldInfoEntry
    new: WorldInfoEntry
    diff: StateDiff


class ChangeDetectionResult(BaseModel):
    """变化检测结果"""
    
    added: List[WorldInfoEntry] = Field(default_factory=list)
    removed: List[WorldInfoEntry] = Field(default_factory=list)
    modified: List[EntryDifference] = Field(default_factory=list)
    unchanged: List[WorldInfoEntry] = Field(default_factory=list)


class ChatChangeResult(BaseModel):
    """对话变化结果"""
    
    type: str = Field(..., description="no_change, append, truncation, modification")
    diff_index: Optional[int] = None
    new_messages: Optional[List[ChatMessage]] = None
    new_messages_count: Optional[int] = None
    removed_messages_count: Optional[int] = None
    details: Optional[List[Dict]] = None
    message_count: int = Field(default=0)
