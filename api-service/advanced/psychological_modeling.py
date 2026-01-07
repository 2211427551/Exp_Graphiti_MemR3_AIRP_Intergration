"""
心理连贯性建模数据模型

定义心理状态实体网络和状态演化跟踪所需的数据结构
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """来源引用"""
    source_type: str = Field(..., description="来源类型")
    source_id: Optional[str] = Field(None, description="来源ID")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")


class EmotionalMix(BaseModel):
    """情绪混合"""
    
    emotion_type: str = Field(..., description="情绪类型：joy, sadness, anger, fear, etc.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="强度 0.0-1.0")
    duration: Optional[float] = Field(None, description="持续时间（秒）")
    triggers: List[str] = Field(default_factory=list, description="触发因素")
    manifestations: List[str] = Field(default_factory=list, description="表现形式")


class TraitManifestation(BaseModel):
    """特质表现"""
    
    trait_name: str = Field(..., description="特质名称")
    strength: float = Field(..., ge=0.0, le=1.0, description="强度 0.0-1.0")
    consistency: float = Field(..., ge=0.0, le=1.0, description="一致性 0.0-1.0（跨时间）")
    behavior_examples: List[str] = Field(default_factory=list, description="行为示例")
    situational_context: str = Field(..., description="情境")


class PsychologicalState(BaseModel):
    """心理状态实体"""
    
    # 核心属性
    entity_id: str = Field(..., description="唯一标识")
    entity_type: Literal["psychological_state"] = "psychological_state"
    character_id: str = Field(..., description="所属角色ID")
    
    # 情绪混合
    emotional_mix: List[EmotionalMix] = Field(default_factory=list, description="情绪混合")
    dominant_emotion: Optional[str] = Field(None, description="主导情绪")
    
    # 特质表现
    trait_manifestations: Dict[str, TraitManifestation] = Field(default_factory=dict, description="特质表现")
    
    # 状态指标
    stability_score: float = Field(..., ge=0.0, le=1.0, description="稳定性得分 0.0-1.0")
    intensity_level: float = Field(..., ge=0.0, le=1.0, description="强度水平 0.0-1.0")
    arousal_level: float = Field(..., ge=0.0, le=1.0, description="唤醒水平 0.0-1.0")
    
    # 时间属性
    observed_at: datetime = Field(default_factory=datetime.now(timezone.utc), description="观测时间")
    valid_from: datetime = Field(default_factory=datetime.now(timezone.utc), description="有效开始时间")
    valid_until: Optional[datetime] = Field(None, description="有效结束时间")
    
    # 来源
    source: SourceRef = Field(..., description="来源")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class StateTransition(BaseModel):
    """心理状态转移记录"""
    
    character_id: str = Field(..., description="角色ID")
    from_state: str = Field(..., description="源状态ID")
    to_state: str = Field(..., description="目标状态ID")
    transition_type: str = Field(..., description="转移类型")
    trigger_event: str = Field(..., description="触发事件")
    transition_reason: str = Field(..., description="转移原因")
    rationality_score: float = Field(..., ge=0.0, le=1.0, description="合理性得分")
    transitioned_at: datetime = Field(default_factory=datetime.now(timezone.utc), description="转移时间")


class CoherenceScore(BaseModel):
    """心理连贯性得分"""
    
    overall_score: float = Field(..., ge=0.0, le=1.0, description="总体得分")
    trait_consistency: float = Field(..., ge=0.0, le=1.0, description="特质一致性得分")
    emotional_rationality: float = Field(..., ge=0.0, le=1.0, description="情绪合理性得分")
    behavioral_consistency: float = Field(..., ge=0.0, le=1.0, description="行为一致性得分")
    memory_rationality: float = Field(..., ge=0.0, le=1.0, description="记忆合理性得分")


class StateDiff(BaseModel):
    """状态差异"""
    
    emotion_changes: List[Dict] = Field(default_factory=list, description="情绪变化")
    trait_changes: List[Dict] = Field(default_factory=list, description="特质变化")
    stability_change: float = Field(default=0.0, description="稳定性变化")
