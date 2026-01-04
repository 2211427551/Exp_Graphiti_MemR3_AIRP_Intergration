"""
搜索数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量限制")
    center_node_uuid: Optional[str] = Field(None, description="可选的中心节点UUID")
    valid_at: Optional[datetime] = Field(None, description="可选的有效时间点（时间旅行）")


class EpisodeSearchResult(BaseModel):
    """Episode搜索结果模型"""
    uuid: str = Field(..., description="Episode UUID")
    fact: Optional[str] = Field(None, description="Episode事实")
    source_node_uuid: Optional[str] = Field(None, description="源节点UUID")
    valid_at: Optional[str] = Field(None, description="生效时间")
    invalid_at: Optional[str] = Field(None, description="失效时间")
    score: Optional[float] = Field(None, description="相关度分数")


class NodeSearchResult(BaseModel):
    """节点搜索结果模型"""
    uuid: str = Field(..., description="节点UUID")
    name: Optional[str] = Field(None, description="节点名称")
    summary: Optional[str] = Field(None, description="节点摘要")
    labels: Optional[List[str]] = Field(None, description="节点标签")
    created_at: Optional[str] = Field(None, description="创建时间")
    attributes: Optional[Dict[str, Any]] = Field(None, description="节点属性")


class SearchResponse(BaseModel):
    """搜索响应模型"""
    success: bool = True
    query: str = Field(..., description="搜索查询")
    results: List[Any] = Field(..., description="搜索结果")
    total: int = Field(..., description="结果总数")


class NodeSearchResponse(BaseModel):
    """节点搜索响应模型"""
    success: bool = True
    query: str = Field(..., description="搜索查询")
    nodes: List[NodeSearchResult] = Field(..., description="节点列表")
    total: int = Field(..., description="节点总数")
    search_type: str = Field(..., description="搜索类型：hybrid/basic")
