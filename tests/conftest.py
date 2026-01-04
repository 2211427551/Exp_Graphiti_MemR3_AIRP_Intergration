"""
pytest配置和fixtures
"""

import pytest
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api_service'))


@pytest.fixture(scope="session")
def test_service():
    """测试服务实例
    
    注意：此fixture需要Neo4j运行
    如果Neo4j未运行，测试会失败
    """
    from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService
    service = EnhancedGraphitiService()
    yield service
    service.close()


@pytest.fixture
def mock_neo4j_env(monkeypatch):
    """模拟Neo4j环境变量"""
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test_password")
    return {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "test_password"
    }


@pytest.fixture
def sample_episode_data():
    """示例Episode数据"""
    return {
        "content": "测试内容：用户Alice今天访问了网站并购买了产品",
        "episode_type": "text",
        "name": "测试Episode",
        "metadata": {
            "user_id": "test_user",
            "action": "visit"
        }
    }
