"""
因果关系统提取器单元测试

测试范围：
- 事件实体提取
- 因果关系识别
- LLM集成
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from advanced.causal_analyzer import CausalAnalyzer


class TestCausalAnalyzer:
    """因果关系统提取器测试"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """创建mock的LLM服务"""
        llm = MagicMock()
        
        # Mock client和response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
{
  "events": [
    {
      "event_name": "沙尘暴",
      "event_type": "incident",
      "participants": ["未花"],
      "location": "沙漠",
      "time": "2026-01-07"
    }
  ],
  "causal_relations": [
    {
      "cause_event": "沙尘暴",
      "effect_event": "迷路",
      "relation_type": "causes",
      "causal_strength": 0.9,
      "necessity_score": 0.8,
      "sufficiency_score": 0.7,
      "conditions": ["沙尘暴持续"],
      "exceptions": ["有向导"],
      "evidence": "因为沙尘暴导致迷路",
      "confidence": 0.85
    }
  ]
}
'''
        
        llm.client.chat.completions.create = AsyncMock(return_value=mock_response)
        return llm
    
    @pytest.fixture
    def analyzer(self, mock_llm_service):
        """创建因果分析器实例"""
        return CausalAnalyzer(mock_llm_service)
    
    @pytest.mark.asyncio
    async def test_extract_causal_relations(self, analyzer):
        """测试提取因果关系"""
        # 测试文本
        text = "未花今天在沙漠中迷路了，因为一场突如其来的沙尘暴。她感到很害怕，但是想到了对策委员会的同伴们，又鼓起了勇气。"
        
        # 执行提取
        result = await analyzer.extract_causal_relations(
            text=text,
            context={"characters": ["未花"], "location": "沙漠", "time": "2026-01-07"}
        )
        
        # 验证返回结构
        assert "events" in result
        assert "causal_relations" in result
        assert isinstance(result["events"], list)
        assert isinstance(result["causal_relations"], list)
        assert "analysis_time" in result
    
    @pytest.mark.asyncio
    async def test_extract_causal_relations_with_context(self, analyzer):
        """测试带上下文的因果关系提取"""
        text = "A导致了B"
        
        result = await analyzer.extract_causal_relations(
            text=text,
            context={"characters": ["角色1"], "location": "地点1", "time": "现在"}
        )
        
        # 应该正常返回
        assert isinstance(result, dict)
        assert "events" in result
    
    def test_parse_events(self, analyzer):
        """测试解析事件数据"""
        # 测试数据
        events_data = [
            {
                "event_name": "沙尘暴",
                "event_type": "incident",
                "participants": ["未花"],
                "location": "沙漠",
                "time": "2026-01-07"
            },
            {
                "event_name": "迷路",
                "event_type": "outcome",
                "participants": ["未花"],
                "location": "沙漠",
                "time": "2026-01-07"
            }
        ]
        
        # 执行解析
        parsed_events = analyzer.parse_events(events_data)
        
        # 验证结果
        assert len(parsed_events) == 2
        assert all("event_id" in event for event in parsed_events)
        assert all("name" in event for event in parsed_events)
        assert all("event_type" in event for event in parsed_events)
    
    def test_parse_events_empty(self, analyzer):
        """测试解析空事件数据"""
        parsed_events = analyzer.parse_events([])
        assert len(parsed_events) == 0
    
    def test_parse_causal_relations(self, analyzer):
        """测试解析因果关系数据"""
        # 测试数据
        relations_data = [
            {
                "cause_event": "沙尘暴",
                "effect_event": "迷路",
                "relation_type": "causes",
                "causal_strength": 0.9,
                "necessity_score": 0.8,
                "sufficiency_score": 0.7,
                "conditions": ["沙尘暴持续"],
                "exceptions": ["有向导"],
                "evidence": "因为沙尘暴",
                "confidence": 0.85
            }
        ]
        
        # 事件映射
        events_map = {
            "沙尘暴": "event_001",
            "迷路": "event_002"
        }
        
        # 执行解析
        parsed_relations = analyzer.parse_causal_relations(relations_data, events_map)
        
        # 验证结果
        assert len(parsed_relations) == 1
        assert "cause_event_id" in parsed_relations[0]
        assert "effect_event_id" in parsed_relations[0]
        assert "relation_type" in parsed_relations[0]
        assert "causal_strength" in parsed_relations[0]
    
    def test_parse_causal_relations_with_missing_event(self, analyzer):
        """测试解析包含不存在事件的因果关系"""
        # 测试数据
        relations_data = [
            {
                "cause_event": "沙尘暴",
                "effect_event": "不存在的结果",
                "relation_type": "causes",
                "causal_strength": 0.9,
                "necessity_score": 0.8,
                "sufficiency_score": 0.7,
                "conditions": [],
                "exceptions": [],
                "evidence": "证据",
                "confidence": 0.85
            }
        ]
        
        # 事件映射（缺少结果事件）
        events_map = {
            "沙尘暴": "event_001"
        }
        
        # 执行解析
        parsed_relations = analyzer.parse_causal_relations(relations_data, events_map)
        
        # 应该返回空列表，因为缺少必要的事件ID
        assert len(parsed_relations) == 0
