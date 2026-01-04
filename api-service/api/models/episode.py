"""
Episode数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class EpisodeCreate(BaseModel):
    """创建Episode请求模型"""
    content: str = Field(..., description="Episode内容（文本或JSON字符串）")
    episode_type: str = Field("text", description="Episode类型：text/json/message")
    name: Optional[str] = Field(None, description="Episode名称（可选）")
    source: Optional[str] = Field(None, description="来源标识")
    source_description: Optional[str] = Field(None, description="来源描述")
    reference_time: Optional[datetime] = Field(None, description="参考时间（可选）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据（可选）")


class EpisodeResult(BaseModel):
    """Episode结果模型"""
    uuid: str = Field(..., description="Episode UUID")
    name: str = Field(..., description="Episode名称")
    message: str = Field(..., description="响应消息")


class EpisodeResponse(BaseModel):
    """Episode响应模型"""
    success: bool = True
    data: EpisodeResult = Field(..., description="Episode数据")
