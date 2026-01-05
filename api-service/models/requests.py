# ============================================
# 请求数据模型
# ============================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    """OpenAI兼容的消息模型"""
    
    role: str = Field(
        ...,
        description="消息角色：system, user, assistant"
    )
    
    content: str = Field(
        ...,
        description="消息内容"
    )
    
    # 可选字段
    name: Optional[str] = Field(
        default=None,
        description="发送者名称（可选）"
    )


class ChatCompletionRequest(BaseModel):
    """OpenAI兼容的Chat Completions请求模型"""
    
    model: str = Field(
        ...,
        description="模型名称，如：deepseek-chat"
    )
    
    messages: List[Message] = Field(
        ...,
        description="消息列表"
    )
    
    # 可选参数
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数（0.0-2.0）"
    )
    
    max_tokens: Optional[int] = Field(
        default=4096,
        ge=1,
        description="最大生成token数"
    )
    
    # 自定义字段（用于会话管理）
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID（可选，用于记忆管理）"
    )
    
    # 其他OpenAI兼容参数
    top_p: Optional[float] = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Top-p采样参数"
    )
    
    n: Optional[int] = Field(
        default=1,
        ge=1,
        description="生成候选数量"
    )
    
    stop: Optional[List[str]] = Field(
        default=None,
        description="停止序列"
    )
    
    presence_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="存在惩罚"
    )
    
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="频率惩罚"
    )
