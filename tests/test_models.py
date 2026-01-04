"""
数据模型测试
"""

import pytest
from datetime import datetime
from api_service.api.models.common import SuccessResponse, ErrorResponse, HealthResponse
from api_service.api.models.episode import EpisodeCreate, EpisodeResult, EpisodeResponse
from api_service.api.models.search import (
    SearchRequest, EpisodeSearchResult, NodeSearchResult,
    SearchResponse, NodeSearchResponse
)


def test_success_response():
    """测试成功响应模型"""
    response = SuccessResponse(
        success=True,
        message="操作成功",
        data={"key": "value"}
    )
    
    assert response.success is True
    assert response.message == "操作成功"
    assert response.data == {"key": "value"}


def test_error_response():
    """测试错误响应模型"""
    response = ErrorResponse(
        success=False,
        error="测试错误",
        details="详细错误信息",
        timestamp="2024-01-01T00:00:00Z"
    )
    
    assert response.success is False
    assert response.error == "测试错误"
    assert response.details == "详细错误信息"
    assert response.timestamp == "2024-01-01T00:00:00Z"


def test_health_response():
    """测试健康检查响应模型"""
    response = HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2024-01-01T00:00:00Z",
        graphiti_core_enabled=True
    )
    
    assert response.status == "healthy"
    assert response.version == "1.0.0"
    assert response.graphiti_core_enabled is True


def test_episode_create():
    """测试创建Episode请求模型"""
    episode = EpisodeCreate(
        content="测试内容",
        episode_type="text",
        name="测试Episode",
        source="test",
        metadata={"key": "value"}
    )
    
    assert episode.content == "测试内容"
    assert episode.episode_type == "text"
    assert episode.name == "测试Episode"
    assert episode.source == "test"
    assert episode.metadata == {"key": "value"}


def test_episode_create_with_datetime():
    """测试创建Episode带时间戳"""
    ref_time = datetime(2024, 1, 15, 10, 30)
    episode = EpisodeCreate(
        content="测试内容",
        episode_type="text",
        reference_time=ref_time
    )
    
    assert episode.reference_time == ref_time


def test_episode_create_defaults():
    """测试创建Episode默认值"""
    episode = EpisodeCreate(content="测试内容")
    
    assert episode.content == "测试内容"
    assert episode.episode_type == "text"
    assert episode.name is None
    assert episode.source is None


def test_episode_result():
    """测试Episode结果模型"""
    result = EpisodeResult(
        uuid="test-uuid",
        name="测试Episode",
        message="创建成功"
    )
    
    assert result.uuid == "test-uuid"
    assert result.name == "测试Episode"
    assert result.message == "创建成功"


def test_episode_response():
    """测试Episode响应模型"""
    result = EpisodeResult(
        uuid="test-uuid",
        name="测试Episode",
        message="创建成功"
    )
    response = EpisodeResponse(
        success=True,
        data=result
    )
    
    assert response.success is True
    assert response.data.uuid == "test-uuid"


def test_search_request():
    """测试搜索请求模型"""
    request = SearchRequest(
        query="测试查询",
        limit=10,
        center_node_uuid="node-uuid",
        valid_at=datetime(2024, 1, 15, 10, 30)
    )
    
    assert request.query == "测试查询"
    assert request.limit == 10
    assert request.center_node_uuid == "node-uuid"


def test_search_request_defaults():
    """测试搜索请求默认值"""
    request = SearchRequest(query="测试")
    
    assert request.query == "测试"
    assert request.limit == 10
    assert request.center_node_uuid is None
    assert request.valid_at is None


def test_search_request_limit_validation():
    """测试搜索请求limit验证"""
    # 有效范围
    request = SearchRequest(query="测试", limit=50)
    assert request.limit == 50
    
    request = SearchRequest(query="测试", limit=1)
    assert request.limit == 1
    
    request = SearchRequest(query="测试", limit=100)
    assert request.limit == 100


def test_episode_search_result():
    """测试Episode搜索结果模型"""
    result = EpisodeSearchResult(
        uuid="episode-uuid",
        fact="测试事实",
        source_node_uuid="node-uuid",
        valid_at="2024-01-01T00:00:00Z",
        invalid_at="2024-01-02T00:00:00Z",
        score=0.95
    )
    
    assert result.uuid == "episode-uuid"
    assert result.fact == "测试事实"
    assert result.score == 0.95


def test_node_search_result():
    """测试节点搜索结果模型"""
    result = NodeSearchResult(
        uuid="node-uuid",
        name="测试节点",
        summary="节点摘要",
        labels=["Entity", "Person"],
        created_at="2024-01-01T00:00:00Z",
        attributes={"key": "value"}
    )
    
    assert result.uuid == "node-uuid"
    assert result.name == "测试节点"
    assert len(result.labels) == 2
    assert "Entity" in result.labels


def test_node_search_result_optional_fields():
    """测试节点搜索结果可选字段"""
    result = NodeSearchResult(uuid="node-uuid")
    
    assert result.uuid == "node-uuid"
    assert result.name is None
    assert result.summary is None
    assert result.labels is None


def test_search_response():
    """测试搜索响应模型"""
    results = [
        EpisodeSearchResult(uuid="1", fact="事实1"),
        EpisodeSearchResult(uuid="2", fact="事实2")
    ]
    response = SearchResponse(
        success=True,
        query="测试",
        results=results,
        total=2
    )
    
    assert response.success is True
    assert response.query == "测试"
    assert len(response.results) == 2
    assert response.total == 2


def test_node_search_response():
    """测试节点搜索响应模型"""
    nodes = [
        NodeSearchResult(uuid="1", name="节点1"),
        NodeSearchResult(uuid="2", name="节点2")
    ]
    response = NodeSearchResponse(
        success=True,
        query="测试",
        nodes=nodes,
        total=2,
        search_type="hybrid"
    )
    
    assert response.success is True
    assert response.search_type == "hybrid"
    assert len(response.nodes) == 2


def test_model_serialization():
    """测试模型序列化"""
    episode = EpisodeCreate(
        content="测试内容",
        episode_type="text"
    )
    
    # 转换为字典
    data = episode.model_dump()
    assert data["content"] == "测试内容"
    assert data["episode_type"] == "text"
    
    # 转换为JSON
    json_data = episode.model_dump_json()
    assert "测试内容" in json_data


def test_model_deserialization():
    """测试模型反序列化"""
    data = {
        "content": "测试内容",
        "episode_type": "text",
        "name": "测试Episode"
    }
    
    episode = EpisodeCreate(**data)
    assert episode.content == "测试内容"
    assert episode.name == "测试Episode"


def test_model_validation():
    """测试模型验证"""
    # 缺少必填字段
    with pytest.raises(Exception):
        EpisodeCreate()
    
    # 无效类型
    with pytest.raises(Exception):
        SearchRequest(query=123)  # 应该是字符串


def test_health_response_minimal():
    """测试健康检查响应最小字段"""
    response = HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2024-01-01T00:00:00Z",
        graphiti_core_enabled=False
    )
    
    assert response.graphiti_core_enabled is False
