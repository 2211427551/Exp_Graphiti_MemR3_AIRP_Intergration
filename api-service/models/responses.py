# ============================================
# 响应数据模型
# ============================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatCompletionMessage(BaseModel):
    """OpenAI兼容的聊天完成消息模型"""
    
    role: str = Field(
        ...,
        description="消息角色：assistant"
    )
    
    content: str = Field(
        ...,
        description="消息内容"
    )


class Usage(BaseModel):
    """OpenAI兼容的使用量统计模型"""
    
    prompt_tokens: int = Field(
        ...,
        description="输入token数"
    )
    
    completion_tokens: int = Field(
        ...,
        description="输出token数"
    )
    
    total_tokens: int = Field(
        ...,
        description="总token数"
    )


class ChatCompletionChoice(BaseModel):
    """OpenAI兼容的聊天完成选项模型"""
    
    index: int = Field(
        default=0,
        description="选项索引"
    )
    
    message: ChatCompletionMessage = Field(
        ...,
        description="完成消息"
    )
    
    finish_reason: str = Field(
        ...,
        description="完成原因：stop, length, content_filter等"
    )


class ChatCompletionResponse(BaseModel):
    """OpenAI兼容的Chat Completions响应模型"""
    
    id: str = Field(
        ...,
        description="请求ID"
    )
    
    object: str = Field(
        default="chat.completion",
        description="对象类型"
    )
    
    created: int = Field(
        ...,
        description="创建时间（Unix时间戳）"
    )
    
    model: str = Field(
        ...,
        description="使用的模型"
    )
    
    choices: List[ChatCompletionChoice] = Field(
        ...,
        description="完成选项列表"
    )
    
    usage: Usage = Field(
        ...,
        description="使用量统计"
    )
    
    # 自定义字段（用于记忆管理）
    extra: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外信息（如记忆使用数量）"
    )


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    
    status: str = Field(
        default="healthy",
        description="健康状态"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="检查时间"
    )
    
    version: str = Field(
        default="1.0.0",
        description="API版本"
    )


class MemorySearchResult(BaseModel):
    """记忆搜索结果模型"""
    
    uuid: str = Field(
        ...,
        description="记忆UUID"
    )
    
    fact: str = Field(
        ...,
        description="记忆内容摘要"
    )
    
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="相关性分数"
    )
    
    valid_at: Optional[str] = Field(
        default=None,
        description="生效时间"
    )
    
    created_at: Optional[str] = Field(
        default=None,
        description="创建时间"
    )
