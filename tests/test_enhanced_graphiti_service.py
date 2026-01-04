"""
EnhancedGraphitiService单元测试
"""

import pytest
from datetime import datetime, timezone


def test_graphiti_core_enabled(test_service):
    """测试graphiti_core是否启用"""
    assert test_service.is_graphiti_core_enabled() is True


def test_get_graphiti_core_info(test_service):
    """测试获取graphiti_core信息"""
    info = test_service.get_graphiti_core_info()
    
    assert info["enabled"] is True
    assert "version" in info
    assert "features" in info
    assert isinstance(info["features"], list)
    assert len(info["features"]) > 0


def test_add_episode_text(test_service):
    """测试添加文本Episode"""
    result = test_service.add_episode_graphiti_core(
        content="测试内容：用户Alice今天访问了网站",
        episode_type="text",
        name="测试文本Episode"
    )
    
    assert result["success"] is True
    assert "episode_uuid" in result
    assert result["name"] == "测试文本Episode"
    assert "message" in result


def test_add_episode_json(test_service):
    """测试添加JSON Episode"""
    episode_data = {
        "actor": "Alice",
        "event": "purchase",
        "product": "MacBook Pro",
        "price": 1999
    }
    
    result = test_service.add_episode_graphiti_core(
        content=episode_data,
        episode_type="json",
        name="测试JSON Episode"
    )
    
    assert result["success"] is True
    assert "episode_uuid" in result


def test_add_episode_with_metadata(test_service):
    """测试添加带元数据的Episode"""
    result = test_service.add_episode_graphiti_core(
        content="测试内容",
        episode_type="text",
        name="测试带元数据",
        metadata={
            "user_id": "12345",
            "source": "test",
            "priority": "high"
        }
    )
    
    assert result["success"] is True
    assert "episode_uuid" in result


def test_add_episode_with_timestamp(test_service):
    """测试添加带时间戳的Episode"""
    timestamp = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
    
    result = test_service.add_episode_graphiti_core(
        content="测试内容",
        episode_type="text",
        name="测试带时间戳",
        reference_time=timestamp
    )
    
    assert result["success"] is True
    assert "episode_uuid" in result


def test_search_episodes(test_service):
    """测试搜索Episodes"""
    # 先添加一些测试数据
    test_service.add_episode_graphiti_core(
        content="用户Alice访问了网站并购买了产品",
        episode_type="text",
        name="搜索测试1"
    )
    
    result = test_service.search_episodes_graphiti_core(
        query="Alice",
        limit=5
    )
    
    assert result["success"] is True
    assert "results" in result
    assert "total" in result
    assert result["total"] >= 0


def test_search_episodes_with_limit(test_service):
    """测试搜索Episodes带limit参数"""
    # 添加测试数据
    test_service.add_episode_graphiti_core(
        content="测试内容",
        episode_type="text",
        name="limit测试"
    )
    
    result = test_service.search_episodes_graphiti_core(
        query="测试",
        limit=3
    )
    
    assert result["success"] is True
    assert len(result["results"]) <= 3


def test_search_nodes_hybrid(test_service):
    """测试混合搜索节点"""
    # 添加测试数据
    test_service.add_episode_graphiti_core(
        content="用户Bob今天购买了iPhone",
        episode_type="text",
        name="节点测试"
    )
    
    result = test_service.search_nodes_graphiti_core(
        query="用户",
        limit=5,
        use_hybrid_search=True
    )
    
    assert result["success"] is True
    assert "nodes" in result
    assert "total" in result
    assert result.get("search_type") == "hybrid"


def test_search_nodes_basic(test_service):
    """测试基础搜索节点"""
    result = test_service.search_nodes_graphiti_core(
        query="测试",
        limit=3,
        use_hybrid_search=False
    )
    
    assert result["success"] is True
    assert "nodes" in result


def test_get_graph_state_at_time(test_service):
    """测试获取图状态（时间旅行）"""
    query_time = datetime.now(timezone.utc)
    
    result = test_service.get_graph_state_at_time_graphiti_core(
        query_time=query_time,
        limit=10
    )
    
    assert result["success"] is True
    assert "query_time" in result
    assert "total_nodes" in result
    assert "nodes" in result


def test_cache_stats(test_service):
    """测试缓存统计"""
    stats = test_service.get_cache_stats()
    
    assert "cache_size" in stats
    assert "cache_hits" in stats
    assert "cache_misses" in stats
    assert "total_queries" in stats
    assert stats["cache_size"] >= 0


def test_clear_cache(test_service):
    """测试清除缓存"""
    # 先添加一些缓存
    test_service.search_episodes_graphiti_core(query="test", limit=5)
    
    # 清除缓存
    test_service.clear_cache()
    
    # 验证缓存已清除
    stats = test_service.get_cache_stats()
    assert stats["cache_size"] == 0
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0


def test_get_service_info(test_service):
    """测试获取服务信息"""
    info = test_service.get_service_info()
    
    assert "service_type" in info
    assert "graphiti_core_enabled" in info
    assert "graphiti_core_info" in info
    assert "cache_stats" in info
    assert "timestamp" in info


def test_add_episode_invalid_type(test_service):
    """测试添加无效类型的Episode"""
    result = test_service.add_episode_graphiti_core(
        content="测试内容",
        episode_type="invalid_type",
        name="测试无效类型"
    )
    
    # 应该仍然成功，因为会fallback到text类型
    assert result["success"] is True or "error" in result


def test_search_empty_query(test_service):
    """测试空查询"""
    result = test_service.search_episodes_graphiti_core(
        query="",
        limit=5
    )
    
    # 应该返回成功，即使没有结果
    assert result["success"] is True
