"""
因果推理引擎单元测试

测试范围：
- 正向推理（从原因推导结果）
- 反向推理（从结果反推原因）
- 跨层级推理
- 冲突检测和解决
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from advanced.causal_reasoning import CausalReasoningEngine


class TestCausalReasoningEngine:
    """因果推理引擎测试"""
    
    @pytest.fixture
    def mock_graphiti_service(self):
        """创建mock的graphiti service"""
        mock_service = MagicMock()
        mock_service.graphiti = AsyncMock()
        mock_service.graphiti.driver = MagicMock()
        return mock_service
    
    @pytest.fixture
    def engine(self, mock_graphiti_service):
        """创建因果推理引擎实例"""
        return CausalReasoningEngine(mock_graphiti_service)
    
    @pytest.mark.asyncio
    async def test_trace_causal_chain_forward(self, engine):
        """测试追踪因果链（正向）"""
        # Mock Cypher查询返回空结果（因为实际数据库连接）
        mock_session = MagicMock()
        mock_session.run.return_value = iter([])
        engine.graphiti_service.graphiti.driver.session.return_value.__enter__.return_value = mock_session
        
        # 执行正向追踪
        chain = await engine.trace_causal_chain(
            start_event_id="event_sandstorm",
            direction="forward",
            max_depth=3
        )
        
        # 验证返回结构
        assert hasattr(chain, "paths")
        assert hasattr(chain, "total_paths")
        assert hasattr(chain, "max_depth")
        assert hasattr(chain, "min_strength")
    
    @pytest.mark.asyncio
    async def test_trace_causal_chain_backward(self, engine):
        """测试追踪因果链（反向）"""
        # Mock Cypher查询返回空结果
        mock_session = MagicMock()
        mock_session.run.return_value = iter([])
        engine.graphiti_service.graphiti.driver.session.return_value.__enter__.return_value = mock_session
        
        # 执行反向追踪
        chain = await engine.trace_causal_chain(
            start_event_id="event_lost",
            direction="backward",
            max_depth=3
        )
        
        # 验证返回结构
        assert hasattr(chain, "paths")
        assert isinstance(chain.paths, list)
    
    @pytest.mark.asyncio
    async def test_deduce_consequences(self, engine):
        """测试推演事件后果"""
        # Mock trace_causal_chain
        from advanced.causal_modeling import CausalChain
        mock_chain = CausalChain(paths=[], total_paths=0, max_depth=0, min_strength=0.0)
        
        # 执行推演
        consequences = await engine.deduce_consequences(
            current_event_id="event_start",
            scenario_conditions={},
            max_depth=3
        )
        
        # 验证返回结果
        assert isinstance(consequences, list)
    
    def test_check_conditions(self, engine):
        """测试检查前提条件"""
        # 测试空条件
        result = engine._check_conditions([], {})
        assert result is True
        
        # 测试有条件但场景不匹配
        result = engine._check_conditions(["角色:未花"], {})
        assert result is False
    
    def test_check_exceptions(self, engine):
        """测试检查例外情况"""
        # 测试空例外
        result = engine._check_exceptions([], {})
        assert result is False
        
        # 测试有例外且场景不匹配（包含冒号）
        # "角色:未花" -> split后是":未花" -> key是"character_:未花"
        result = engine._check_exceptions(["角色:未花"], {"character_未花": True})
        assert result is False  # key不匹配
        
        # 测试有例外且场景匹配（不包含冒号）
        result = engine._check_exceptions(["角色 未花"], {"character_未花": True})
        assert result is True  # key匹配
