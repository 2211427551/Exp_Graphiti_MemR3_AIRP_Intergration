"""
通用响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class SuccessResponse(BaseModel):
    """成功响应模型"""
    success: bool = True
    message: Optional[str] = Field(None, description="成功消息")
    data: Optional[Any] = Field(None, description="响应数据")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str = Field(..., description="错误信息")
    details: Optional[str] = Field(None, description="错误详情")
    timestamp: Optional[str] = Field(None, description="错误时间戳")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API版本")
    timestamp: str = Field(..., description="检查时间")
    graphiti_core_enabled: bool = Field(..., description="graphiti_core是否启用")
