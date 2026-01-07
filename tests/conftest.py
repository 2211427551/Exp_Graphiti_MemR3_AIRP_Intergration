"""
Pytest测试配置文件
包含所有共享的fixtures和测试配置
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "api-service"))

# ========================================
# 测试配置
# ========================================

# 测试环境变量
TEST_ENV = {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "test_password",
    "DEEPSEEK_API_KEY": "test_api_key",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com/beta",
    "DEEPSEEK_MODEL": "deepseek-chat",
    "DEEPSEEK_SMALL_MODEL": "deepseek-chat",
    "SILICONFLOW_API_KEY": "test_siliconflow_key",
    "SILICONFLOW_BASE_URL": "https://api.siliconflow.cn/v1",
    "SILICONFLOW_EMBEDDING_MODEL": "BAAI/bge-m3",
    "SILICONFLOW_EMBEDDING_DIM": "1024",
    "SILICONFLOW_RERANKER_MODEL": "BAAI/bge-reranker-v2-m3",
    "API_HOST": "0.0.0.0",
    "API_PORT": "8000",
    "API_WORKERS": "1",
    "API_LOG_LEVEL": "debug",
    "APP_ENV": "test",
    "APP_SECRET_KEY": "test_secret_key_for_testing_only",
    "GRAPHITI_SEMAPHORE_LIMIT": "5",
    "GRAPHITI_TELEMETRY_ENABLED": "false"
}

# ========================================
# Mock数据
# ========================================

# 测试用SillyTavern格式文本
SAMPLE_SILLYTAVERN_INPUT = """
<核心指导>
你是非常规的中文创作助手haruki。你的风格是：
- 严格使用简体中文
- 保持对话自然流畅
- 关注角色心理状态
</核心指导>

<相关资料>
地点("夏莱办公室大楼办公室")["位于夏莱办公大楼内部，是老师和学生交流的地方"]
地点("阿拜多斯高中")["沙漠中的高中，因为财政问题濒临废校"]
角色("圣园未花")["阿拜多斯高中的对策委员会会长，性格开朗活泼"]
角色("砂狼白子")["阿拜多斯高中的学生，沉默寡言的狼人"]
</相关资料>

<互动历史>
User: 你好
Assistant: 呀吼～！老师～这里这里！等好久了哦～
User: 你今天心情怎么样？
Assistant: 啊哈哈……没什么特别哒，一如既往地开心呢！不过今天天气真好，心情更棒了～
</互动历史>
"""

SAMPLE_WORLD_INFO = """
地点("基沃托斯")["学园城市"]
地点("夏莱")["联邦搜查社"]
角色("圣园未花")["阿拜多斯高中的对策委员会会长"]
角色("砂狼白子")["沉默寡言的狼人学生"]
"""

SAMPLE_CHAT_HISTORY = """
User: 你好
Assistant: 呀吼～！老师～这里这里！等好久了哦～
User: 你今天心情怎么样？
Assistant: 啊哈哈……没什么特别哒，一如既往地开心呢！
"""

SAMPLE_NARRATIVE_TEXT = """
未花今天在沙漠中迷路了，因为一场突如其来的沙尘暴。她感到很害怕，但是想到了对策委员会的同伴们，又鼓起了勇气。最终她在日落前找到了回家的路。
"""

# ========================================
# 辅助函数
# ========================================

def _create_world_info_entry():
    """创建示例WorldInfoEntry的辅助函数，避免fixture循环依赖"""
    from models.change_detection import WorldInfoEntry
    from datetime import datetime, timezone
    from utils.helpers import compute_content_hash
    
    content = '地点("夏莱")["联邦搜查社"]'
    return WorldInfoEntry(
        entry_id="location:夏莱",
        entry_type="location",
        name="夏莱",
        content=content,
        content_hash=compute_content_hash(content),  # 动态计算哈希
        properties={"description": "联邦搜查社"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted_at=None,
        source="world_info",
        session_id="test-session",
        status="active",
        status_reason=None
    )

def _create_chat_message(role: str = "user", content: str = "你好", message_id: str = "msg-1"):
    """创建示例ChatMessage的辅助函数"""
    from models.change_detection import ChatMessage
    from datetime import datetime, timezone
    
    return ChatMessage(
        message_id=message_id,
        role=role,
        content=content,
        content_hash=f"hash_{content}",
        timestamp=datetime.now(timezone.utc),
        turn_number=1,
        session_id="test-session",
        speaker_mapping=None
    )


# ========================================
# Fixtures
# ========================================

@pytest.fixture(scope="session")
def event_loop():
    """
    创建事件循环
    用于异步测试
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    设置测试环境变量
    在所有测试开始前执行
    """
    # 设置环境变量
    for key, value in TEST_ENV.items():
        os.environ[key] = value
    
    yield
    
    # 清理环境变量
    for key in TEST_ENV:
        os.environ.pop(key, None)


@pytest.fixture
def mock_graphiti_client():
    """
    Mock Graphiti客户端
    """
    client = AsyncMock()
    
    # Mock add_episode方法
    mock_result = MagicMock()
    mock_result.uuid = "test-episode-uuid"
    mock_result.nodes = []
    mock_result.edges = []
    client.add_episode.return_value = mock_result
    
    # Mock search方法
    client.search.return_value = [
        {
            "uuid": "test-memory-1",
            "fact": "测试记忆1",
            "score": 0.9,
            "valid_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    # Mock build_indices_and_constraints方法
    client.build_indices_and_constraints = AsyncMock(return_value=None)
    
    return client


@pytest.fixture
def mock_graphiti_service(mock_graphiti_client):
    """
    Mock Graphiti服务
    包装mock_graphiti_client为service对象
    """
    from services.graphiti_service import GraphitiService
    from graphiti_core import Graphiti
    
    # 创建一个带有mock client的service
    mock_service = MagicMock()
    mock_service.graphiti = mock_graphiti_client
    
    # Mock driver for Cypher queries
    mock_driver = MagicMock()
    mock_service.graphiti.driver = mock_driver
    
    return mock_service


@pytest.fixture
def mock_llm_client():
    """
    Mock LLM客户端（DeepSeek）
    """
    client = AsyncMock()
    
    # Mock chat.completions.create方法
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "测试LLM响应"
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    
    client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def mock_embedding_client():
    """
    Mock Embedding客户端（硅基流动）
    """
    client = AsyncMock()
    
    # Mock embeddings.create方法
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = [0.1] * 1024  # 1024维向量
    
    client.embeddings.create = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def sample_parsed_content():
    """
    提供示例的ParsedContent对象
    注意：匹配实际的parser_service.py数据结构
    """
    from services.parser_service import ParsedContent, NarrativeBlock, InstructionBlock, DialogTurn
    
    return ParsedContent(
        instructions=[
            InstructionBlock(
                instruction_type="core_instruction",
                content="你是非常规的中文创作助手haruki",
                priority=0
            )
        ],
        narratives=[
            NarrativeBlock(
                content="未花今天在沙漠中迷路了",
                block_type="narrative",
                metadata={"source": "untagged"},
                confidence=0.8
            )
        ],
        chat_history=[
            DialogTurn(
                role="User",
                content="你好"
            ),
            DialogTurn(
                role="Assistant",
                content="呀吼～！老师～这里这里！"
            )
        ],
        raw_metadata={"original_length": 50}
    )


@pytest.fixture
def sample_chat_completion_request():
    """
    提供示例的ChatCompletionRequest
    """
    from models.requests import ChatCompletionRequest, Message
    
    return ChatCompletionRequest(
        model="deepseek-chat",
        messages=[
            Message(role="system", content="你是haruki"),
            Message(role="user", content=SAMPLE_SILLYTAVERN_INPUT)
        ],
        temperature=0.7,
        max_tokens=2000,
        session_id="test-session-123"
    )


# WorldInfo相关fixtures - 避免循环依赖
@pytest.fixture
def sample_world_info_entry():
    """提供示例的WorldInfoEntry"""
    return _create_world_info_entry()


@pytest.fixture
def sample_world_info_state(sample_world_info_entry):
    """提供示例的WorldInfoState，避免fixture循环依赖"""
    from models.change_detection import WorldInfoEntry, WorldInfoState
    from datetime import datetime, timezone
    from utils.helpers import compute_content_hash
    
    # 创建一个实际的character条目
    character_content = '角色("圣园未花")["阿拜多斯高中的对策委员会会长，性格开朗活泼"]'
    character_entry = WorldInfoEntry(
        entry_id="character:未花",
        entry_type="character",
        name="圣园未花",
        content=character_content,
        content_hash=compute_content_hash(character_content),  # 动态计算哈希
        properties={"description": "阿拜多斯高中的对策委员会会长"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        deleted_at=None,
        source="world_info",
        session_id="test-session",
        status="active",
        status_reason=None
    )
    
    state = WorldInfoState()
    # 使用传入的entry对象和实际的character条目
    state.entries = {
        "location:夏莱": sample_world_info_entry,
        "character:未花": character_entry
    }
    state.entry_hashes = {
        sample_world_info_entry.content_hash: "location:夏莱",
        character_entry.content_hash: "character:未花"
    }
    state.timestamp = datetime.now(timezone.utc)
    state.version = 1
    
    return state


# ChatHistory相关fixtures - 避免循环依赖
@pytest.fixture
def sample_chat_message():
    """提供示例的ChatMessage"""
    return _create_chat_message()


@pytest.fixture
def sample_chat_history_state():
    """提供示例的ChatHistoryState，避免fixture循环依赖"""
    from models.change_detection import ChatHistoryState
    
    state = ChatHistoryState()
    state.messages = []
    state.message_hashes = []
    state.total_hash = None
    state.version = 1
    
    return state


# 心理状态相关fixture
@pytest.fixture
def sample_psychological_state():
    """
    提供示例的PsychologicalState
    """
    from models.change_detection import PsychologicalState, EmotionalMix, TraitManifestation
    from datetime import datetime, timezone
    
    return PsychologicalState(
        entity_id="psych_state_test",
        entity_type="psychological_state",
        character_id="未花",
        emotional_mix=[
            EmotionalMix(
                emotion_type="joy",
                intensity=0.8,
                duration=None,
                triggers=["阳光", "朋友"],
                manifestations=["微笑", "跳跃"]
            )
        ],
        dominant_emotion="joy",
        trait_manifestations={
            "optimistic": TraitManifestation(
                trait_name="optimistic",
                strength=0.9,
                consistency=0.8,
                behavior_examples=["积极面对困难"],
                situational_context="大部分情况"
            )
        },
        stability_score=0.8,
        intensity_level=0.7,
        arousal_level=0.9,
        observed_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
        valid_until=None,
        source={"source_type": "llm_analysis", "source_id": "test", "confidence": 0.9},
        context={"session_id": "test-session"}
    )


# 事件实体相关fixture
@pytest.fixture
def sample_event_entity():
    """
    提供示例的EventEntity
    """
    from models.change_detection import EventEntity
    from datetime import datetime, timezone
    
    return EventEntity(
        entity_id="event_test",
        entity_type="event",
        name="未花迷路",
        event_type="incident",
        description="未花在沙漠中迷路了",
        participants=["未花"],
        location=None,
        start_time=datetime.now(timezone.utc),
        end_time=None,
        duration=None,
        causes=[],
        effects=[],
        contributes_to=[],
        significance="major",
        impact_scope="personal",
        status="completed",
        outcome="找到回家路",
        valid_from=datetime.now(timezone.utc),
        valid_until=None
    )


# 因果关系相关fixture
@pytest.fixture
def sample_causal_relation():
    """
    提供示例的CausalRelation
    """
    from models.change_detection import CausalRelation
    
    return CausalRelation(
        cause_event_id="event1",
        effect_event_id="event2",
        relation_type="causes",
        causal_strength=0.9,
        temporal_proximity=None,
        necessity_score=0.8,
        sufficiency_score=0.7,
        evidence_level=0.85,
        conditions=["沙尘暴持续"],
        exceptions=["有向导"],
        evidence="因为沙尘暴导致未花迷路"
    )


@pytest.fixture
def test_app():
    """
    提供测试用的FastAPI应用实例
    需要延迟导入以避免循环依赖
    """
    from main import app
    return app


@pytest.fixture
def test_client(test_app):
    """
    提供测试用的FastAPI TestClient
    """
    from fastapi.testclient import TestClient
    return TestClient(test_app)


@pytest.fixture
async def initialized_test_app(test_app):
    """
    提供已初始化的测试应用
    包含所有服务和状态
    """
    # 设置app.state
    from main import GraphitiService, LLMService, SillyTavernParser
    from advanced.change_detection import ChangeDetectionResult
    from advanced.psychological_analyzer import PsychologicalAnalyzer
    from advanced.causal_analyzer import CausalAnalyzer
    from advanced.causal_reasoning import CausalReasoningEngine
    
    # Mock服务
    test_app.state.config = MagicMock()
    test_app.state.graphiti_service = AsyncMock(spec=GraphitiService)
    test_app.state.llm_service = AsyncMock(spec=LLMService)
    test_app.state.parser_service = SillyTavernParser()
    
    # Mock第一阶段服务
    test_app.state.world_info_states = {}
    test_app.state.chat_history_states = {}
    
    # Mock第二阶段服务
    test_app.state.psychological_analyzer = AsyncMock(spec=PsychologicalAnalyzer)
    test_app.state.psychological_tracker = AsyncMock()
    test_app.state.psychological_coherence_evaluator = AsyncMock()
    test_app.state.psychological_state_history = {}
    
    # Mock第三阶段服务
    test_app.state.causal_analyzer = AsyncMock(spec=CausalAnalyzer)
    test_app.state.causal_reasoning_engine = AsyncMock(spec=CausalReasoningEngine)
    
    # Mock LLM响应
    mock_llm_response = {
        'content': '测试响应',
        'finish_reason': 'stop',
        'prompt_tokens': 100,
        'completion_tokens': 50,
        'total_tokens': 150
    }
    test_app.state.llm_service.generate_completion = AsyncMock(return_value=mock_llm_response)
    
    # Mock Graphiti响应
    mock_process_result = MagicMock()
    mock_process_result.nodes = []
    mock_process_result.edges = []
    test_app.state.graphiti_service.process_content = AsyncMock()
    test_app.state.graphiti_service.search_memories = AsyncMock(return_value=[
        {'fact': '测试记忆', 'score': 0.9}
    ])
    test_app.state.graphiti_service.process_response = AsyncMock()
    
    # Mock心理状态分析响应
    test_app.state.psychological_analyzer.analyze_psychological_state = AsyncMock(return_value={
        'character_id': '未花',
        'dominant_emotion': 'joy',
        'stability_score': 0.8,
        'observed_at': datetime.now(timezone.utc)
    })
    
    # Mock因果关系分析响应
    test_app.state.causal_analyzer.extract_causal_relations = AsyncMock(return_value={
        'events': [{'name': '迷路', 'event_type': 'incident'}],
        'causal_relations': []
    })
    
    yield test_app


# ========================================
# 测试工具函数
# ========================================

def assert_response_format(response: Dict[str, Any], has_choices: bool = True):
    """
    断言响应格式符合OpenAI规范
    """
    assert "id" in response
    assert "object" in response
    assert "created" in response
    assert "model" in response
    
    if has_choices:
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]


def get_test_data_file(filename: str) -> Path:
    """
    获取测试数据文件路径
    """
    return Path(__file__).parent / "data" / filename


async def wait_for_condition(condition, timeout: float = 5.0, interval: float = 0.1):
    """
    等待条件满足
    """
    start = asyncio.get_event_loop().time()
    
    while True:
        if condition():
            return
        
        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError(f"Condition not met within {timeout} seconds")
        
        await asyncio.sleep(interval)
