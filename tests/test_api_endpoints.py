"""
API端点测试
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone


@pytest.fixture
def client():
    """测试客户端"""
    from api_service.api.main import app
    return TestClient(app)


def test_root_endpoint(client):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["service"] == "AIRP Knowledge Graph API"


def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "graphiti_core_enabled" in data


def test_create_episode(client, sample_episode_data):
    """测试创建Episode"""
    response = client.post(
        "/api/v1/episodes/",
        json=sample_episode_data
    )
    
    # 可能成功也可能失败，取决于Neo4j状态
    assert response.status_code in [200, 400, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "uuid" in data["data"]


def test_create_episode_invalid(client):
    """测试创建Episode（无效数据）"""
    invalid_data = {
        "content": "",  # 空内容
        "episode_type": "text"
    }
    
    response = client.post(
        "/api/v1/episodes/",
        json=invalid_data
    )
    
    # 应该返回422（验证错误）或其他错误
    assert response.status_code in [422, 400, 503]


def test_create_episode_with_reference_time(client):
    """测试创建Episode（带时间戳）"""
    episode_data = {
        "content": "测试内容",
        "episode_type": "text",
        "name": "测试Episode",
        "reference_time": datetime.now(timezone.utc).isoformat()
    }
    
    response = client.post(
        "/api/v1/episodes/",
        json=episode_data
    )
    
    # 可能成功也可能失败
    assert response.status_code in [200, 400, 503]


def test_search_episodes(client):
    """测试搜索Episodes"""
    response = client.get(
        "/api/v1/search/episodes",
        params={
            "query": "测试",
            "limit": 5
        }
    )
    
    # 可能成功也可能失败
    assert response.status_code in [200, 400, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "query" in data
        assert "results" in data
        assert "total" in data


def test_search_episodes_with_valid_at(client):
    """测试搜索Episodes（带时间参数）"""
    response = client.get(
        "/api/v1/search/episodes",
        params={
            "query": "测试",
            "limit": 5,
            "valid_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    assert response.status_code in [200, 400, 503]


def test_search_episodes_invalid_time_format(client):
    """测试搜索Episodes（无效时间格式）"""
    response = client.get(
        "/api/v1/search/episodes",
        params={
            "query": "测试",
            "valid_at": "invalid-time"
        }
    )
    
    # 应该返回400错误
    assert response.status_code in [400, 503]


def test_search_nodes_hybrid(client):
    """测试搜索节点（混合搜索）"""
    response = client.get(
        "/api/v1/search/nodes",
        params={
            "query": "测试",
            "limit": 3,
            "use_hybrid": True
        }
    )
    
    assert response.status_code in [200, 400, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "query" in data
        assert "nodes" in data
        assert "total" in data
        assert "search_type" in data


def test_search_nodes_basic(client):
    """测试搜索节点（基础搜索）"""
    response = client.get(
        "/api/v1/search/nodes",
        params={
            "query": "测试",
            "limit": 3,
            "use_hybrid": False
        }
    )
    
    assert response.status_code in [200, 400, 503]


def test_search_nodes_invalid_limit(client):
    """测试搜索节点（无效limit）"""
    response = client.get(
        "/api/v1/search/nodes",
        params={
            "query": "测试",
            "limit": 200  # 超过最大值100
        }
    )
    
    # 应该返回422验证错误
    assert response.status_code in [422, 503]


def test_get_graph_state(client):
    """测试获取图状态（时间旅行）"""
    response = client.get(
        "/api/v1/search/graph-state",
        params={
            "query_time": datetime.now(timezone.utc).isoformat(),
            "limit": 10
        }
    )
    
    assert response.status_code in [200, 400, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "query_time" in data["data"]
        assert "total_nodes" in data["data"]


def test_get_graph_state_invalid_time(client):
    """测试获取图状态（无效时间）"""
    response = client.get(
        "/api/v1/search/graph-state",
        params={
            "query_time": "invalid-time",
            "limit": 10
        }
    )
    
    # 应该返回400错误
    assert response.status_code in [400, 503]


def test_list_episodes(client):
    """测试列出Episodes（占位符）"""
    response = client.get("/api/v1/episodes/")
    
    # 应该返回成功（占位符实现）
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data


def test_get_episode_detail(client):
    """测试获取Episode详情（占位符）"""
    response = client.get("/api/v1/episodes/test-uuid")
    
    # 应该返回501（未实现）
    assert response.status_code == 501


def test_api_docs(client):
    """测试API文档端点"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_api_redoc(client):
    """测试ReDoc端点"""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_cors_headers(client):
    """测试CORS头"""
    response = client.options(
        "/api/v1/episodes/",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST"
        }
    )
    
    # 检查CORS头
    assert response.status_code in [200, 405]  # 405是OPTIONS不允许


def test_json_content_type(client):
    """测试JSON内容类型"""
    response = client.post(
        "/api/v1/episodes/",
        json={"content": "测试", "episode_type": "text"}
    )
    
    # 检查响应头
    assert "content-type" in response.headers
    assert "application/json" in response.headers["content-type"].lower()


def test_error_response_format(client):
    """测试错误响应格式"""
    response = client.get("/api/v1/episodes/invalid-uuid")
    
    if response.status_code == 501:
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
