"""
搜索功能路由
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
from api_service.api.models.search import (
    SearchResponse, NodeSearchResponse,
    EpisodeSearchResult, NodeSearchResult
)
from api_service.api.models.common import SuccessResponse

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


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


@router.get("/episodes", response_model=SearchResponse)
async def search_episodes(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(10, ge=1, le=100, description="返回结果数量"),
    center_node_uuid: Optional[str] = Query(None, description="可选的中心节点UUID"),
    valid_at: Optional[str] = Query(None, description="可选的有效时间点（ISO格式）"),
    service = Depends(get_service)
):
    """
    搜索Episodes
    
    支持语义搜索、时间旅行查询和基于图的重新排序
    """
    try:
        # 转换时间参数
        valid_time = None
        if valid_at:
            try:
                valid_time = datetime.fromisoformat(valid_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="时间格式错误，请使用ISO格式")
        
        result = service.search_episodes_graphiti_core(
            query=query,
            limit=limit,
            center_node_uuid=center_node_uuid,
            valid_at=valid_time
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "搜索失败"))
        
        return SearchResponse(
            success=True,
            query=query,
            results=result["results"],
            total=result["total"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索Episodes失败: {str(e)}")


@router.get("/nodes", response_model=NodeSearchResponse)
async def search_nodes(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(5, ge=1, le=50, description="返回结果数量"),
    use_hybrid: bool = Query(True, description="使用混合搜索（语义+BM25）"),
    service = Depends(get_service)
):
    """
    搜索节点（混合搜索）
    
    使用语义搜索和BM25的混合检索，提供更好的搜索结果
    """
    try:
        result = service.search_nodes_graphiti_core(
            query=query,
            limit=limit,
            use_hybrid_search=use_hybrid
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "搜索失败"))
        
        # 转换节点数据
        nodes = []
        for node_data in result["nodes"]:
            nodes.append(NodeSearchResult(**node_data))
        
        return NodeSearchResponse(
            success=True,
            query=query,
            nodes=nodes,
            total=result["total"],
            search_type=result.get("search_type", "hybrid")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索节点失败: {str(e)}")


@router.get("/graph-state")
async def get_graph_state(
    query_time: str = Query(..., description="查询时间点（ISO格式）"),
    limit: int = Query(100, ge=1, le=500, description="返回结果数量"),
    service = Depends(get_service)
):
    """
    获取指定时间点的图状态（时间旅行）
    
    返回在指定时间点有效的所有实体和关系
    """
    try:
        # 转换时间参数
        query_dt = datetime.fromisoformat(query_time.replace('Z', '+00:00'))
        
        result = service.get_graph_state_at_time_graphiti_core(
            query_time=query_dt,
            limit=limit
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "获取图状态失败"))
        
        return SuccessResponse(
            success=True,
            data={
                "query_time": result["query_time"],
                "total_nodes": result["total_nodes"],
                "nodes": result["nodes"]
            }
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="时间格式错误，请使用ISO格式")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图状态失败: {str(e)}")
