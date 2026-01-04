"""
Episode管理路由
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
from api_service.api.models.episode import EpisodeCreate, EpisodeResult, EpisodeResponse
from api_service.api.models.common import SuccessResponse, ErrorResponse

router = APIRouter(prefix="/api/v1/episodes", tags=["Episodes"])


# 全局服务实例
_service_instance = None


def get_service():
    """获取服务实例（依赖注入）"""
    global _service_instance
    
    if _service_instance is None:
        from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService
        _service_instance = EnhancedGraphitiService()
    
    if not _service_instance.is_graphiti_core_enabled():
        raise HTTPException(status_code=503, detail="graphiti_core未启用或初始化失败")
    
    return _service_instance


@router.post("/", response_model=EpisodeResponse)
async def create_episode(
    episode: EpisodeCreate,
    service = Depends(get_service)
):
    """
    创建Episode
    
    将文本或JSON数据添加到知识图谱
    """
    try:
        # 转换datetime为ISO字符串
        reference_time = None
        if episode.reference_time:
            reference_time = episode.reference_time.isoformat()
        
        result = service.add_episode_graphiti_core(
            content=episode.content,
            episode_type=episode.episode_type,
            name=episode.name,
            source=episode.source,
            source_description=episode.source_description,
            reference_time=reference_time,
            metadata=episode.metadata
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "创建Episode失败"))
        
        return EpisodeResponse(
            success=True,
            data=EpisodeResult(
                uuid=result["episode_uuid"],
                name=result["name"],
                message=result["message"]
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建Episode失败: {str(e)}")


@router.get("/")
async def list_episodes(
    limit: int = 10,
    service = Depends(get_service)
):
    """
    列出所有Episodes（占位符）
    
    注意：graphiti_core主要提供搜索功能，不支持列出所有Episodes
    建议使用搜索功能
    """
    return {
        "success": True,
        "message": "建议使用搜索功能，graphiti_core不支持列出所有Episodes",
        "search_endpoint": "/api/v1/search/episodes"
    }


@router.get("/{episode_id}")
async def get_episode(episode_id: str, service = Depends(get_service)):
    """
    获取Episode详情（占位符）
    
    注意：此功能尚未实现，建议使用搜索功能
    """
    raise HTTPException(
        status_code=501,
        detail="此功能尚未实现，建议使用搜索功能：/api/v1/search/episodes"
    )
