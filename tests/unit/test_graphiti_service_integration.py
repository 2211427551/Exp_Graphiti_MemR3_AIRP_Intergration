"""
GraphitiService高级功能集成测试

测试变化检测、心理连贯性和因果推理的服务层集成
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# 导入被测试的模块
from services.graphiti_service import GraphitiService
from models.change_detection import WorldInfoState, ChatHistoryState, WorldInfoEntry, ChatMessage
from config.settings import AppSettings


# ========================================
# 固件（Fixtures）
# ========================================

@pytest.fixture
def mock_settings():
    """测试用的配置对象"""
    settings = MagicMock(spec=AppSettings)
    return settings


@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti客户端"""
    client = AsyncMock()
    
    # Mock add_episode
    mock_episode_result = MagicMock()
    mock_episode_result.uuid = "test-episode-uuid"
    mock_episode_result.nodes = []
    mock_episode_result.edges = []
    client.add_episode = AsyncMock(return_value=mock_episode_result)
    
    # Mock driver for Cypher queries
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    # Mock execute result
    client.driver = mock_driver
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = [mock_result]
    
    return client


@pytest.fixture
def mock_llm_service():
    """Mock LLM服务"""
    llm = AsyncMock()
    
    # Mock generate_completion
    llm.generate_completion = AsyncMock(return_value={
        'content': '测试响应',
        'finish_reason': 'stop',
        'prompt_tokens': 100,
        'completion_tokens': 50,
        'total_tokens': 150
    })
    
    return llm


@pytest.fixture
def initialized_graphiti_service(mock_settings, mock_graphiti_client, mock_llm_service):
    """已初始化的GraphitiService（包含高级功能）"""
    service = GraphitiService(mock_settings)
    
    # 异步初始化
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(service.initialize(mock_graphiti_client, mock_llm_service))
    
    yield service
    
    # 清理
    loop.close()


@pytest.fixture
def sample_parsed_content():
    """示例的解析内容"""
    from services.parser_service import ParsedContent, NarrativeBlock, DialogTurn
    
    return {
        'world_info': [
            {
                'content': '地点("夏莱")["联邦搜查社"]',
                'type': 'location'
            },
            {
                'content': '角色("未花")["对策委员会会长"]',
                'type': 'character'
            }
        ],
        'world_info_content': '地点("夏莱")["联邦搜查社"]\n角色("未花")["对策委员会会长"]',
        'chat_history': [
            DialogTurn(role='User', content='你好'),
            DialogTurn(role='Assistant', content='呀吼～')
        ],
        'chat_history_content': 'User: 你好\nAssistant: 呀吼～',
        'narratives': [
            NarrativeBlock(
                content='未花在沙漠中迷路了',
                block_type='narrative',
                metadata={},
                confidence=0.9
            )
        ]
    }


@pytest.fixture
def sample_old_world_info_state():
    """旧的WorldInfoState"""
    from utils.helpers import compute_content_hash
    from datetime import datetime, timezone
    
    entry = WorldInfoEntry(
        entry_id="location:夏莱",
        entry_type="location",
        name="夏莱",
        content='地点("夏莱")["联邦搜查社"]',
        content_hash=compute_content_hash('地点("夏莱")["联邦搜查社"]'),
        properties={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted_at=None,
        source="world_info",
        session_id="test-session",
        status="active",
        status_reason=None
    )
    
    state = WorldInfoState()
    state.entries = {"location:夏莱": entry}
    state.entry_hashes = {entry.content_hash: "location:夏莱"}
    state.timestamp = datetime.now(timezone.utc)
    state.version = 1
    
    return state


@pytest.fixture
def sample_old_chat_history_state():
    """旧的ChatHistoryState"""
    from models.change_detection import ChatMessage
    from datetime import datetime, timezone
    
    state = ChatHistoryState()
    msg1 = ChatMessage(
        message_id="msg_1",
        role="User",
        content="你好",
        content_hash="hash_user_hello",
        timestamp=datetime.now(timezone.utc),
        turn_number=1,
        session_id="test-session",
        speaker_mapping=None
    )
    
    state.messages = [msg1]
    state.message_hashes = ["hash_user_hello"]
    state.version = 1
    
    return state


# ========================================
# 测试：初始化
# ========================================

def test_graphiti_service_initialization(mock_settings):
    """测试GraphitiService初始化"""
    service = GraphitiService(mock_settings)
    
    assert service.graphiti is None
    assert service.world_info_states == {}
    assert service.chat_history_states == {}
    assert service.psychological_coherence is None
    assert service.psychological_tracker is None
    assert service.causal_analyzer is None
    assert service.causal_reasoning is None


def test_graphiti_service_initialize_with_llm(mock_settings, mock_graphiti_client, mock_llm_service):
    """测试GraphitiService初始化（带LLM服务）"""
    import asyncio
    service = GraphitiService(mock_settings)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(service.initialize(mock_graphiti_client, mock_llm_service))
    
    assert service.graphiti == mock_graphiti_client
    assert service.psychological_coherence is not None
    assert service.psychological_tracker is not None
    assert service.causal_analyzer is not None
    assert service.causal_reasoning is not None
    
    loop.close()


def test_graphiti_service_initialize_without_llm(mock_settings, mock_graphiti_client):
    """测试GraphitiService初始化（不带LLM服务）"""
    import asyncio
    service = GraphitiService(mock_settings)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(service.initialize(mock_graphiti_client, None))
    
    assert service.graphiti == mock_graphiti_client
    # 高级功能模块应该为None
    assert service.psychological_coherence is None
    assert service.psychological_tracker is None
    assert service.causal_analyzer is None
    assert service.causal_reasoning is None
    
    loop.close()


# ========================================
# 测试：变化检测集成
# ========================================

@pytest.mark.asyncio
async def test_process_content_with_change_detection_new_session(
    initialized_graphiti_service,
    sample_parsed_content
):
    """测试变化检测（新会话，所有条目都是新增）"""
    session_id = "test-session-new"
    
    result = await initialized_graphiti_service.process_content_with_change_detection(
        session_id=session_id,
        parsed_content=sample_parsed_content
    )
    
    # 验证返回结果
    assert "changes_detected" in result
    assert "sync_stats" in result
    assert "stats" in result
    
    # 如果有world_info，验证变化检测结果
    if "world_info" in result["changes_detected"]:
        assert "added" in result["changes_detected"]["world_info"]
        assert "removed" in result["changes_detected"]["world_info"]
        assert "modified" in result["changes_detected"]["world_info"]
    
    # 如果有chat_history，验证变化检测结果
    if "chat_history" in result["changes_detected"]:
        assert "type" in result["changes_detected"]["chat_history"]
        assert "message_count" in result["changes_detected"]["chat_history"]


@pytest.mark.asyncio
async def test_process_content_with_change_detection_with_old_state(
    initialized_graphiti_service,
    sample_parsed_content,
    sample_old_world_info_state,
    sample_old_chat_history_state
):
    """测试变化检测（有旧状态）"""
    session_id = "test-session-existing"
    
    # 设置旧状态
    initialized_graphiti_service.world_info_states[session_id] = sample_old_world_info_state
    initialized_graphiti_service.chat_history_states[session_id] = sample_old_chat_history_state
    
    result = await initialized_graphiti_service.process_content_with_change_detection(
        session_id=session_id,
        parsed_content=sample_parsed_content
    )
    
    # 验证返回结果
    assert "changes_detected" in result
    assert "sync_stats" in result
    assert "stats" in result
    
    # 注意：如果parsed_content没有world_info或chat_history属性，变化检测不会执行
    # 这个测试主要验证方法不会崩溃，返回结果结构正确
    # 如果需要测试实际的变化检测逻辑，需要创建一个带有world_info属性的ParsedContent对象


def test_get_session_state_new_session(initialized_graphiti_service):
    """测试获取新会话状态"""
    session_id = "test-session-new"
    
    state = initialized_graphiti_service.get_session_state(session_id)
    
    assert state["session_id"] == session_id
    assert state["world_info_state"]["version"] == 0
    assert state["world_info_state"]["entry_count"] == 0
    assert state["chat_history_state"]["version"] == 0
    assert state["chat_history_state"]["message_count"] == 0


def test_get_session_state_existing(initialized_graphiti_service, sample_old_world_info_state, sample_old_chat_history_state):
    """测试获取已存在会话状态"""
    session_id = "test-session-existing"
    
    # 设置状态
    initialized_graphiti_service.world_info_states[session_id] = sample_old_world_info_state
    initialized_graphiti_service.chat_history_states[session_id] = sample_old_chat_history_state
    
    state = initialized_graphiti_service.get_session_state(session_id)
    
    assert state["session_id"] == session_id
    assert state["world_info_state"]["version"] >= 1
    assert state["world_info_state"]["entry_count"] >= 1
    assert state["chat_history_state"]["version"] >= 1


# ========================================
# 测试：心理连贯性集成
# ========================================

@pytest.mark.asyncio
async def test_evaluate_psychological_coherence(initialized_graphiti_service):
    """测试评估心理连贯性"""
    character_id = "character_test"
    
    # Mock心理连贯性评估器
    mock_coherence = MagicMock()
    mock_coherence.overall_score = 0.85
    mock_coherence.trait_consistency = 0.90
    mock_coherence.emotional_rationality = 0.82
    mock_coherence.behavioral_consistency = 0.88
    mock_coherence.memory_rationality = 0.80
    
    initialized_graphiti_service.psychological_coherence.evaluate_coherence = AsyncMock(
        return_value=mock_coherence
    )
    
    result = await initialized_graphiti_service.evaluate_psychological_coherence(
        character_id=character_id,
        time_window_days=7
    )
    
    assert result is not None
    assert result["character_id"] == character_id
    assert result["overall_score"] == 0.85
    assert result["trait_consistency"] == 0.90
    assert result["emotional_rationality"] == 0.82


@pytest.mark.asyncio
async def test_evaluate_psychological_coherence_not_initialized(mock_settings, mock_graphiti_client):
    """测试心理连贯性评估（未初始化）"""
    service = GraphitiService(mock_settings)
    
    # 初始化时传入None作为llm_service
    await service.initialize(mock_graphiti_client, None)
    
    result = await service.evaluate_psychological_coherence(
        character_id="test",
        time_window_days=7
    )
    
    # 应该返回None因为心理连贯性评估器未初始化
    assert result is None


@pytest.mark.asyncio
async def test_track_psychological_state_transition(initialized_graphiti_service):
    """测试跟踪心理状态转移"""
    character_id = "character_test"
    old_state = {"dominant_emotion": "sad", "stability_score": 0.5}
    new_state = {"dominant_emotion": "happy", "stability_score": 0.8}
    trigger_event = "positive_interaction"
    
    # Mock心理状态跟踪器
    initialized_graphiti_service.psychological_tracker.track_state_transition = AsyncMock(return_value=None)
    
    result = await initialized_graphiti_service.track_psychological_state_transition(
        character_id=character_id,
        old_state=old_state,
        new_state=new_state,
        trigger_event=trigger_event
    )
    
    assert result is True
    initialized_graphiti_service.psychological_tracker.track_state_transition.assert_called_once()


@pytest.mark.asyncio
async def test_track_psychological_state_transition_not_initialized(mock_settings, mock_graphiti_client):
    """测试心理状态转移跟踪（未初始化）"""
    service = GraphitiService(mock_settings)
    
    # 初始化时传入None作为llm_service
    await service.initialize(mock_graphiti_client, None)
    
    result = await service.track_psychological_state_transition(
        character_id="test",
        old_state={},
        new_state={},
        trigger_event="test"
    )
    
    # 应该返回False
    assert result is False


def test_get_character_psychological_history(initialized_graphiti_service):
    """测试获取角色心理状态历史"""
    character_id = "character_test"
    
    # Mock心理状态跟踪器
    mock_states = [
        {"dominant_emotion": "happy", "timestamp": datetime.now(timezone.utc)},
        {"dominant_emotion": "sad", "timestamp": datetime.now(timezone.utc)}
    ]
    
    initialized_graphiti_service.psychological_tracker.get_character_history = MagicMock(
        return_value=mock_states
    )
    
    history = initialized_graphiti_service.get_character_psychological_history(
        character_id=character_id,
        limit=50
    )
    
    assert len(history) == 2
    assert history[0]["dominant_emotion"] == "happy"
    initialized_graphiti_service.psychological_tracker.get_character_history.assert_called_once_with(
        character_id=character_id,
        limit=50
    )


def test_get_character_psychological_history_not_initialized(mock_settings, mock_graphiti_client):
    """测试获取心理状态历史（未初始化）"""
    service = GraphitiService(mock_settings)
    
    # 初始化时传入None作为llm_service
    # 注意：这个测试不是async的，需要手动处理
    service.graphiti = mock_graphiti_client
    # 不初始化高级功能模块
    
    history = service.get_character_psychological_history(
        character_id="test",
        limit=50
    )
    
    # 应该返回空列表
    assert history == []


# ========================================
# 测试：因果推理集成
# ========================================

@pytest.mark.asyncio
async def test_extract_causal_relations(initialized_graphiti_service):
    """测试提取因果关系"""
    text = "未花迷路了，这导致了她感到害怕"
    context = {"characters": ["未花"], "location": "沙漠"}
    
    # Mock因果分析器
    mock_analysis = {
        "events": [
            {"event_name": "未花迷路", "event_type": "incident"}
        ],
        "causal_relations": [
            {
                "cause_event": "未花迷路",
                "effect_event": "感到害怕",
                "relation_type": "causes",
                "causal_strength": 0.9
            }
        ],
        "analysis_time": datetime.now(timezone.utc).isoformat()
    }
    
    initialized_graphiti_service.causal_analyzer.extract_causal_relations = AsyncMock(
        return_value=mock_analysis
    )
    
    result = await initialized_graphiti_service.extract_causal_relations(
        text=text,
        context=context
    )
    
    assert result is not None
    assert "events" in result
    assert "causal_relations" in result
    assert len(result["events"]) == 1
    assert len(result["causal_relations"]) == 1
    # 只检查被调用，不检查具体参数
    initialized_graphiti_service.causal_analyzer.extract_causal_relations.assert_called_once()


@pytest.mark.asyncio
async def test_extract_causal_relations_not_initialized(mock_settings, mock_graphiti_client):
    """测试提取因果关系（未初始化）"""
    service = GraphitiService(mock_settings)
    
    # 初始化时传入None作为llm_service
    await service.initialize(mock_graphiti_client, None)
    
    result = await service.extract_causal_relations(
        text="测试文本",
        context={}
    )
    
    # 应该返回None
    assert result is None


@pytest.mark.asyncio
async def test_trace_causal_chain_forward(initialized_graphiti_service):
    """测试追踪因果链（前向）"""
    start_event_id = "event_123"
    
    # Mock因果推理引擎
    from advanced.causal_modeling import CausalChain
    mock_chain = CausalChain(
        paths=[
            {
                "events": [
                    {"id": "event_123", "name": "事件A"},
                    {"id": "event_456", "name": "事件B"}
                ],
                "relations": [
                    {"type": "causes", "strength": 0.9}
                ]
            }
        ],
        total_paths=1,
        max_depth=2,
        min_strength=0.7
    )
    
    initialized_graphiti_service.causal_reasoning.trace_causal_chain = AsyncMock(
        return_value=mock_chain
    )
    
    result = await initialized_graphiti_service.trace_causal_chain(
        start_event_id=start_event_id,
        direction="forward",
        max_depth=5,
        min_strength=0.7,
        session_id="test-session"
    )
    
    assert result is not None
    assert result["start_event_id"] == start_event_id
    assert result["direction"] == "forward"
    assert result["total_paths"] == 1
    assert result["max_depth"] == 2
    assert len(result["paths"]) == 1


@pytest.mark.asyncio
async def test_trace_causal_chain_backward(initialized_graphiti_service):
    """测试追踪因果链（反向）"""
    start_event_id = "event_456"
    
    # Mock因果推理引擎
    from advanced.causal_modeling import CausalChain
    mock_chain = CausalChain(
        paths=[],
        total_paths=0,
        max_depth=0,
        min_strength=0.0
    )
    
    initialized_graphiti_service.causal_reasoning.trace_causal_chain = AsyncMock(
        return_value=mock_chain
    )
    
    result = await initialized_graphiti_service.trace_causal_chain(
        start_event_id=start_event_id,
        direction="backward",
        max_depth=3,
        min_strength=0.6,
        session_id="test-session"
    )
    
    assert result is not None
    assert result["direction"] == "backward"


@pytest.mark.asyncio
async def test_trace_causal_chain_not_initialized(mock_settings, mock_graphiti_client):
    """测试追踪因果链（未初始化）"""
    service = GraphitiService(mock_settings)
    
    # 初始化时传入None作为llm_service
    await service.initialize(mock_graphiti_client, None)
    
    result = await service.trace_causal_chain(
        start_event_id="event_123",
        direction="forward",
        max_depth=5,
        min_strength=0.7
    )
    
    # 应该返回None
    assert result is None


@pytest.mark.asyncio
async def test_deduce_consequences(initialized_graphiti_service):
    """测试推演事件后果"""
    current_event_id = "event_123"
    scenario_conditions = {"character_未花": "scared"}
    
    # Mock因果推理引擎
    from advanced.causal_modeling import Consequence
    mock_consequences = [
        Consequence(
            event_id="event_456",
            event_description="未花会寻找帮助",
            probability=0.9,
            steps=1,
            conditions_needed=["其他人在附近"],
            exceptions=["独自一人"],
            causal_path={}
        ),
        Consequence(
            event_id="event_789",
            event_description="未花会感到绝望",
            probability=0.6,
            steps=2,
            conditions_needed=[],
            exceptions=["找到出路"],
            causal_path={}
        )
    ]
    
    initialized_graphiti_service.causal_reasoning.deduce_consequences = AsyncMock(
        return_value=mock_consequences
    )
    
    result = await initialized_graphiti_service.deduce_consequences(
        current_event_id=current_event_id,
        scenario_conditions=scenario_conditions,
        max_depth=3,
        min_strength=0.6,
        session_id="test-session"
    )
    
    assert result is not None
    assert len(result) == 2
    assert result[0]["event_description"] == "未花会寻找帮助"
    assert result[0]["probability"] == 0.9
    assert result[1]["probability"] == 0.6


@pytest.mark.asyncio
async def test_deduce_consequences_not_initialized(mock_settings, mock_graphiti_client):
    """测试推演事件后果（未初始化）"""
    service = GraphitiService(mock_settings)
    
    # 初始化时传入None作为llm_service
    await service.initialize(mock_graphiti_client, None)
    
    result = await service.deduce_consequences(
        current_event_id="event_123",
        scenario_conditions={},
        max_depth=3,
        min_strength=0.6
    )
    
    # 应该返回None
    assert result is None


# ========================================
# 测试：错误处理
# ========================================

@pytest.mark.asyncio
async def test_evaluate_psychological_coherence_error_handling(initialized_graphiti_service):
    """测试心理连贯性评估的错误处理"""
    # Mock抛出异常
    initialized_graphiti_service.psychological_coherence.evaluate_coherence = AsyncMock(
        side_effect=Exception("模拟错误")
    )
    
    result = await initialized_graphiti_service.evaluate_psychological_coherence(
        character_id="test",
        time_window_days=7
    )
    
    # 应该返回None而不是抛出异常
    assert result is None


@pytest.mark.asyncio
async def test_extract_causal_relations_error_handling(initialized_graphiti_service):
    """测试提取因果关系的错误处理"""
    # Mock抛出异常
    initialized_graphiti_service.causal_analyzer.extract_causal_relations = AsyncMock(
        side_effect=Exception("模拟错误")
    )
    
    result = await initialized_graphiti_service.extract_causal_relations(
        text="测试",
        context={}
    )
    
    # 应该返回None而不是抛出异常
    assert result is None


@pytest.mark.asyncio
async def test_trace_causal_chain_error_handling(initialized_graphiti_service):
    """测试追踪因果链的错误处理"""
    # Mock抛出异常
    initialized_graphiti_service.causal_reasoning.trace_causal_chain = AsyncMock(
        side_effect=Exception("模拟错误")
    )
    
    result = await initialized_graphiti_service.trace_causal_chain(
        start_event_id="event_123",
        direction="forward",
        max_depth=5,
        min_strength=0.7
    )
    
    # 应该返回None而不是抛出异常
    assert result is None
