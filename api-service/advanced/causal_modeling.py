"""
因果逻辑链建模数据模型

定义因果链、事件和因果关系所需的数据结构
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field


class EventEntity(BaseModel):
    """事件实体"""
    
    # 核心属性
    entity_id: str = Field(..., description="唯一标识")
    entity_type: Literal["event"] = "event"
    name: str = Field(..., description="事件名称")
    event_type: str = Field(..., description="事件类型：action, incident, outcome, etc.")
    description: str = Field(..., description="事件描述")
    
    # 参与者
    participants: List[str] = Field(default_factory=list, description="参与角色ID列表")
    location: Optional[str] = Field(None, description="地点ID")
    
    # 时间属性
    start_time: datetime = Field(default_factory=datetime.now(timezone.utc), description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="持续时间（秒）")
    
    # 因果关系
    causes: List[str] = Field(default_factory=list, description="导致此事件的事件ID列表")
    effects: List[str] = Field(default_factory=list, description="此事件导致的事件ID列表")
    contributes_to: List[str] = Field(default_factory=list, description="此事件促成的目标/事件ID列表")
    
    # 重要性
    significance: str = Field(default="minor", description="重要性：critical, major, minor, trivial")
    impact_scope: str = Field(default="local", description="影响范围")
    
    # 状态
    status: str = Field(default="planned", description="状态：planned, ongoing, completed, failed, cancelled")
    outcome: Optional[str] = Field(None, description="结果")
    
    # 时间属性
    valid_from: datetime = Field(default_factory=datetime.now(timezone.utc), description="有效开始时间")
    valid_until: Optional[datetime] = Field(None, description="有效结束时间")


class CausalRelation(BaseModel):
    """因果关系"""
    
    cause_event_id: str = Field(..., description="原因事件ID")
    effect_event_id: str = Field(..., description="结果事件ID")
    
    # 关系类型
    relation_type: str = Field(..., description="causes, contributes_to, prevents, enables, requires")
    
    # 关系强度和可信度
    causal_strength: float = Field(..., ge=0.0, le=1.0, description="因果强度 0.0-1.0")
    temporal_proximity: Optional[float] = Field(None, description="时间接近度")
    
    # 必要性和充分性
    necessity_score: float = Field(..., ge=0.0, le=1.0, description="必要性得分 0.0-1.0")
    sufficiency_score: float = Field(..., ge=0.0, le=1.0, description="充分性得分 0.0-1.0")
    
    # 证据和置信度
    evidence_level: float = Field(..., ge=0.0, le=1.0, description="证据级别 0.0-1.0")
    evidence: str = Field(default="", description="证据或理由")
    
    # 条件和例外
    conditions: List[str] = Field(default_factory=list, description="前提条件列表")
    exceptions: List[str] = Field(default_factory=list, description="例外情况")
    
    # 时间属性
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc), description="创建时间")


class CausalChain(BaseModel):
    """因果链"""
    
    paths: List[Dict] = Field(default_factory=list, description="因果路径列表")
    total_paths: int = Field(default=0, description="总路径数")
    max_depth: int = Field(default=0, description="最大深度")
    min_strength: float = Field(default=0.0, description="最小因果强度")


class Consequence(BaseModel):
    """事件后果"""
    
    event_id: str = Field(..., description="事件ID")
    event_description: str = Field(..., description="事件描述")
    probability: float = Field(..., ge=0.0, le=1.0, description="可能性 0.0-1.0")
    steps: int = Field(default=0, description="距离当前事件的步数")
    conditions_needed: List[str] = Field(default_factory=list, description="需要的条件")
    exceptions: List[str] = Field(default_factory=list, description="例外情况")
