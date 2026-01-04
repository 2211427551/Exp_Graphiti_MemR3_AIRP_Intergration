"""
健康检查路由
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from api_service.api.models.common import HealthResponse, ErrorResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    try:
        # 尝试获取服务信息
        from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService
        
        # 创建临时服务实例检查状态
        service = EnhancedGraphitiService()
        try:
            graphiti_enabled = service.is_graphiti_core_enabled()
        finally:
            service.close()
        
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            graphiti_core_enabled=graphiti_enabled
        )
    except Exception as e:
        # 如果健康检查失败，返回错误但不抛出异常
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            graphiti_core_enabled=False
        )


@router.get("/")
async def root():
    """根路径"""
    return {
        "service": "AIRP Knowledge Graph API",
        "version": "1.0.0",
        "description": "基于graphiti_core的双时序知识图谱API",
        "docs": "/docs",
        "health": "/health"
    }
