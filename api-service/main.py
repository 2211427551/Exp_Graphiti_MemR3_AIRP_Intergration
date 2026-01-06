"""
============================================
FastAPI主应用入口
============================================

基于Graphiti的记忆增强系统，为SillyTavern提供OpenAI兼容API
支持变化检测、心理连贯性建模和因果逻辑链
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any

# 导入配置和服务
from config.settings import load_app_config
from config.graphiti_config import GraphitiClientFactory
from services.parser_service import SillyTavernParser
from services.graphiti_service import GraphitiService
from services.llm_service import LLMService
from models.requests import ChatCompletionRequest
from models.responses import ChatCompletionResponse, HealthResponse

# 导入原有服务
from api_service.models.change_detection import (
    WorldInfoEntry,
    WorldInfoState,
    ChatMessage,
    ChatHistoryState
)

# 导入第一阶段：变化检测与同步
from api_service.advanced.change_detection import (
    detect_worldinfo_changes,
    detect_chat_changes,
    update_world_info_state,
    update_chat_history_state,
    ChangeDetectionResult,
    ChatChangeResult
)
from api_service.advanced.change_sync import (
    process_added_entries,
    process_removed_entries,
    process_modified_entries
)

# 导入第二阶段：心理连贯性建模
from api_service.advanced.psychological_analyzer import PsychologicalAnalyzer
from api_service.advanced.psychological_tracker import PsychologicalStateTracker
from api_service.advanced.psychological_coherence import PsychologicalCoherenceEvaluator
from api_service.models.change_detection import (
    PsychologicalState,
    StateTransition,
    CoherenceScore
)

# 导入第三阶段：因果逻辑链建模
from api_service.advanced.causal_analyzer import CausalAnalyzer
from api_service.advanced.causal_reasoning import CausalReasoningEngine
from api_service.advanced.causal_storage import store_causal_chain
from api_service.models.change_detection import (
    EventEntity,
    CausalRelation,
    CausalChain,
    Consequence
)

# 导入辅助函数
from api_service.advanced.causal_analyzer import CausalAnalyzer

# 全局变量
graphiti_service: GraphitiService = None
llm_service: LLMService = None
parser_service: SillyTavernParser = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    
    功能：
        启动时：初始化所有服务
        关闭时：清理所有资源
    """
    global graphiti_service, llm_service, parser_service
    
    # 启动阶段
    logger.info("=" * 60)
    logger.info("AIRP记忆系统启动中...")
    logger.info("=" * 60)
    
    # 步骤1: 加载应用配置
    logger.info("加载应用配置...")
    config = load_app_config()
    app.state.config = config
    logger.info(f"运行环境: {config.env}")
    logger.info(f"API监听地址: {config.api.host}:{config.api.port}")
    
    # 步骤2: 初始化Graphiti客户端
    logger.info("初始化Graphiti客户端...")
    graphiti_client = await GraphitiClientFactory.create_graphiti_client(
        neo4j_uri=config.neo4j.uri,
        neo4j_user=config.neo4j.user,
        neo4j_password=config.neo4j.password,
        deepseek_api_key=config.deepseek.api_key,
        deepseek_base_url=config.deepseek.base_url,
        deepseek_model=config.deepseek.model,
        deepseek_small_model=config.deepseek.small_model,
        siliconflow_api_key=config.siliconflow.api_key,
        siliconflow_base_url=config.siliconflow.base_url,
        siliconflow_embedding_model=config.siliconflow.embedding_model,
        siliconflow_embedding_dim=config.siliconflow.embedding_dim,
        siliconflow_reranker_model=config.siliconflow.reranker_model,
        semaphore_limit=config.api.semaphore_limit
    )
    logger.info("Graphiti客户端初始化成功")
    
    # 步骤3: 初始化服务
    logger.info("初始化服务层...")
    graphiti_service = GraphitiService(graphiti_client)
    llm_service = LLMService(
        api_key=config.deepseek.api_key,
        base_url=config.deepseek.base_url,
        model=config.deepseek.model
    )
    parser_service = SillyTavernParser()
    logger.info("所有服务初始化完成")
    
    # 步骤4-6: 初始化第一阶段服务（变化检测与同步）
    logger.info("初始化第一阶段服务（变化检测与同步）...")
    # 状态跟踪器（在内存中，生产环境可用Redis）
    app.state.world_info_states = {}
    app.state.chat_history_states = {}
    logger.info("第一阶段服务初始化完成")
    
    # 步骤7-8: 初始化第二阶段服务（心理连贯性建模）
    logger.info("初始化第二阶段服务（心理连贯性建模）...")
    app.state.psychological_analyzer = PsychologicalAnalyzer(llm_service=llm_service)
    app.state.psychological_tracker = PsychologicalStateTracker(graphiti_service=graphiti_service)
    app.state.psychological_coherence_evaluator = PsychologicalCoherenceEvaluator(graphiti_service=graphiti_service)
    app.state.psychological_state_history = {}  # character_id -> [states]
    logger.info("第二阶段服务初始化完成")
    
    # 步骤9-10: 初始化第三阶段服务（因果逻辑链建模）
    logger.info("初始化第三阶段服务（因果逻辑链建模）...")
    app.state.causal_analyzer = CausalAnalyzer(llm_service=llm_service)
    app.state.causal_reasoning_engine = CausalReasoningEngine(graphiti_service=graphiti_service)
    logger.info("第三阶段服务初始化完成")
    
    # 存储到app.state
    app.state.graphiti_service = graphiti_service
    app.state.llm_service = llm_service
    app.state.parser_service = parser_service
    
    logger.info("=" * 60)
    logger.info("AIRP记忆系统启动完成")
    logger.info("=" * 60)
    
    yield
    
    # 关闭阶段
    logger.info("关闭AIRP记忆系统...")
    await GraphitiClientFactory.close_graphiti_client(graphiti_client)
    await llm_service.close()
    logger.info("AIRP记忆系统已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="AIRP Memory System",
    description="基于Graphiti的记忆增强系统，支持变化检测、心理连贯性和因果逻辑链，为SillyTavern提供OpenAI兼容API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# 健康检查端点（增强版，包含状态信息）
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查端点
    
    返回:
        HealthResponse: 健康状态，包含各模块状态
    """
    world_info_count = len(app.state.world_info_states)
    chat_history_count = len(app.state.chat_history_states)
    psych_state_count = sum(len(states) for states in app.state.psychological_state_history.values())
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        world_info_states=world_info_count,
        chat_history_states=chat_history_count,
        psych_state_records=psych_state_count
    )


# OpenAI兼容端点
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest
):
    """
    OpenAI兼容的Chat Completions端点
    
    支持功能：
    - 变化检测与同步（World Info、Chat History）
    - 心理连贯性建模（分析、跟踪、评估）
    - 因果逻辑链建模（提取、存储、推演）
    - 记忆处理、检索和优化
    - LLM调用和响应处理
    
    返回:
        ChatCompletionResponse: OpenAI兼容的响应
    """
    # 获取服务实例
    graphiti_svc = request.app.state.graphiti_service
    llm_svc = request.app.state.llm_service
    parser_svc = request.app.state.parser_service
    
    # 步骤1: 提取session_id
    session_id = _extract_session_id(request, body)
    logger.info(f"收到请求 - 会话ID: {session_id}")
    
    # 步骤2: 提取最后一个user消息
    last_user_message = _extract_last_user_message(body.messages)
    logger.debug(f"最后一条用户消息长度: {len(last_user_message.content)}")
    
    # 步骤3: 解析SillyTavern格式
    parsed_content = parser_svc.parse(last_user_message.content)
    logger.debug(f"解析结果 - 指令: {len(parsed_content.instructions)}, 叙事: {len(parsed_content.narratives)}, 对话: {len(parsed_content.chat_history)}")
    
    # ========================================
    # 第一阶段：变化检测与同步
    # ========================================
    
    # 步骤4.1: World Info变化检测
    if parsed_content.world_info:
        old_world_info_state = app.state.world_info_states.get(session_id)
        
        if old_world_info_state:
            logger.info("检测World Info变化...")
            # 检测变化
            changes = detect_worldinfo_changes(
                old_state=old_world_info_state,
                new_content=parsed_content.world_info_content
            )
            
            # 记录变化
            logger.info(f"World Info变化 - 新增: {len(changes.get('added', []))}, 删除: {len(changes.get('removed', []))}, 修改: {len(changes.get('modified', []))}")
            
            # 同步到Graphiti
            if changes.get("added"):
                logger.info(f"同步{len(changes['added'])}个新增条目...")
                stats = await process_added_entries(
                    graphiti_service=graphiti_svc,
                    entries=changes["added"],
                    session_id=session_id
                )
                logger.info(f"新增完成 - 实体: {stats['entities_created']}, 关系: {stats['relationships_created']}")
            
            if changes.get("removed"):
                logger.info(f"同步{len(changes['removed'])}个删除条目...")
                stats = await process_removed_entries(
                    graphiti_service=graphiti_svc,
                    entries=changes["removed"],
                    session_id=session_id
                )
                logger.info(f"删除完成 - 标记删除: {stats['episodes_marked_deleted']}")
            
            if changes.get("modified"):
                logger.info(f"同步{len(changes['modified'])}个修改条目...")
                stats = await process_modified_entries(
                    graphiti_service=graphiti_svc,
                    modifications=changes["modified"],
                    session_id=session_id
                )
                logger.info(f"修改完成 - 旧版本superseded: {stats['old_episodes_superseded']}, 新版本: {stats['new_episodes_created']}")
            
            # 更新状态跟踪器
            new_world_info_state = update_world_info_state(
                old_world_info_state,
                changes
            )
            app.state.world_info_states[session_id] = new_world_info_state
            logger.info("World Info状态已更新")
        else:
            logger.info("首次World Info，所有条目将作为新增处理")
            # 首次：直接处理（通过process_content实现）
    
    # 步骤4.2: Chat History变化检测
    if parsed_content.chat_history:
        old_chat_history_state = app.state.chat_history_states.get(session_id)
        
        if old_chat_history_state:
            logger.info("检测Chat History变化...")
            # 检测变化
            chat_changes = detect_chat_changes(
                old_state=old_chat_history_state,
                new_content=parsed_content.chat_history_content,
                session_id=session_id
            )
            
            # 记录变化
            logger.info(f"Chat History变化类型: {chat_changes.type}")
            if chat_changes.new_messages:
                logger.info(f"新增{chat_changes.new_messages_count}条消息")
            if chat_changes.removed_messages_count:
                logger.info(f"删除{chat_changes.removed_messages_count}条消息")
            
            # 更新状态跟踪器
            new_chat_history_state = update_chat_history_state(
                old_chat_history_state,
                chat_changes
            )
            app.state.chat_history_states[session_id] = new_chat_history_state
            logger.info("Chat History状态已更新")
        else:
            logger.info("首次Chat History，将正常处理")
    
    # ========================================
    # 第二阶段：心理连贯性建模
    # ========================================
    
    # 步骤5: 心理状态分析
    if parsed_content.chat_history:
        # 识别主要角色（从对话历史中）
        main_character_id = _identify_main_character(parsed_content.chat_history)
        
        if main_character_id:
            logger.info(f"分析角色'{main_character_id}'的心理状态...")
            
            # 提取最近的对话
            recent_dialogs = parsed_content.chat_history[-5:]  # 最近5轮
            
            # 构建对话文本
            dialog_text = "\n".join([
                f"{msg.role}: {msg.content}" 
                for msg in recent_dialogs
            ])
            
            # 分析心理状态
            try:
                new_state = await app.state.psychological_analyzer.analyze_psychological_state(
                    character_id=main_character_id,
                    dialog_text=dialog_text,
                    context={
                        "session_id": session_id,
                        "character_description": _get_character_description(main_character_id)
                    }
                )
                
                # 获取旧状态（如果存在）
                old_state = _get_last_psychological_state(app.state, main_character_id)
                
                # 跟踪状态转移
                if old_state:
                    await app.state.psychological_tracker.track_state_transition(
                        character_id=main_character_id,
                        old_state=old_state,
                        new_state=new_state,
                        trigger_event="dialog_interaction"
                    )
                
                # 存储新状态到Graphiti
                await _store_psychological_state(
                    graphiti_service=graphiti_svc,
                    state=new_state,
                    session_id=session_id
                )
                
                # 更新历史
                if main_character_id not in app.state.psychological_state_history:
                    app.state.psychological_state_history[main_character_id] = []
                app.state.psychological_state_history[main_character_id].append(new_state)
                
                logger.info(f"角色'{main_character_id}'心理状态分析完成 - 主导情绪: {new_state['dominant_emotion']}, 稳定性: {new_state['stability_score']:.2f}")
                
            except Exception as e:
                logger.error(f"分析角色'{main_character_id}'的心理状态时出错: {e}")
    
    # ========================================
    # 第三阶段：因果逻辑链建模
    # ========================================
    
    # 步骤6: 因果关系提取
    if parsed_content.narratives:
        logger.info("提取因果关系...")
        
        # 处理每个叙事性内容
        for narrative in parsed_content.narratives:
            # 提取因果关系
            analysis_result = await app.state.causal_analyzer.extract_causal_relations(
                text=narrative.content,
                context={
                    "session_id": session_id,
                    "characters": _get_all_characters(parsed_content.chat_history),
                    "character_description": _get_character_description(_identify_main_character(parsed_content.chat_history))
                }
            )
            
            # 解析事件和因果关系
            events = app.state.causal_analyzer.parse_events(
                analysis_result.get("events", [])
            )
            relations = app.state.causal_analyzer.parse_causal_relations(
                analysis_result.get("causal_relations", []),
                {event["name"]: f"event_{i}" for i, event in enumerate(events)}
            )
            
            # 存储到Graphiti
            stats = await store_causal_chain(
                graphiti_service=graphiti_svc,
                events=events,
                causal_relations=relations,
                session_id=session_id
            )
            
            logger.info(f"因果链存储完成 - 事件: {stats['events_stored']}, 关系: {stats['relations_stored']}")
    
    # ========================================
    # 原有流程：记忆处理、检索、优化、LLM调用、响应处理
    # ========================================
    
    # 步骤7: 记忆处理
    logger.info("处理内容到Graphiti...")
    await graphiti_svc.process_content(
        session_id=session_id,
        parsed_content=parsed_content
    )
    
    # 步骤8: 记忆检索
    logger.info("检索相关记忆...")
    related_memories = await graphiti_svc.search_memories(
        session_id=session_id,
        query=last_user_message.content,
        limit=10
    )
    logger.info(f"检索到{len(related_memories)}条相关记忆")
    
    # 步骤9: 上下文优化
    optimized_messages = _optimize_context(
        original_messages=body.messages,
        parsed_content=parsed_content,
        memories=related_memories
    )
    logger.debug(f"优化后消息数: {len(optimized_messages)}")
    
    # 步骤10: LLM调用
    logger.info("调用LLM生成响应...")
    completion_response = await llm_svc.generate_completion(
        model=body.model,
        messages=optimized_messages,
        temperature=body.temperature,
        max_tokens=body.max_tokens
    )
    logger.info(f"LLM响应完成 - tokens: {completion_response.get('total_tokens', 0)}")
    
    # 步骤11: 响应后处理（异步）
    logger.info("异步处理响应内容...")
    asyncio.create_task(
        graphiti_svc.process_response(
            session_id=session_id,
            response_content=completion_response['content']
        )
    )
    
    # 步骤12: 返回OpenAI兼容响应
    return _format_chat_completion_response(
        completion_response=completion_response,
        model=body.model,
        memories_count=len(related_memories)
    )


# ========================================
# 辅助函数实现
# ========================================

def _extract_session_id(request: Request, body: ChatCompletionRequest) -> str:
    """
    提取会话ID
    
    优先级：
        1. 自定义header: X-Session-ID
        2. 请求参数: session_id
        3. 系统消息内容: 解析SESSION_ID
    
    返回:
        str: 会话ID
    """
    # 方式1: 自定义header
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        return session_id
    
    # 方式2: 请求参数
    if hasattr(body, 'session_id') and body.session_id:
        return body.session_id
    
    # 方式3: 系统消息内容
    for message in body.messages:
        if message.role == "system":
            # 查找SESSION_ID
            import re
            match = re.search(r'SESSION_ID\s*[:]\s*([^\s]+)', message.content)
            if match:
                return match.group(1).strip()
    
    # 默认：生成新ID
    return f"sess-{uuid.uuid4()}"


def _extract_last_user_message(messages: list) -> dict:
    """
    提取最后一个user消息
    
    参数:
        messages: list
                消息列表
    
    返回:
        dict: 最后一个user消息
    
    异常:
        HTTPException: 未找到user消息
    """
    for message in reversed(messages):
        if message.role == "user":
            return message
    
    raise HTTPException(status_code=400, detail="No user message found")


def _identify_main_character(chat_history: list) -> Optional[str]:
    """
    从对话历史中识别主要角色
    
    策略：
        第一个非User角色的原始名称
    
    返回:
        Optional[str]: 主要角色的speaker_mapping
    """
    if not chat_history:
        return None
    
    for turn in chat_history:
        if turn.role == "assistant":
            return turn.speaker_mapping
    
    return None


def _get_character_description(character_id: str) -> str:
    """
    从Graphiti获取角色描述
    
    参数:
        character_id: str
                角色ID
    
    返回:
        str: 角色描述
    
    当前实现：返回占位符
    TODO: 实现从Graphiti查询
    """
    return f"角色_{character_id}的描述"


def _get_all_characters(chat_history: list) -> List[str]:
    """
    获取对话历史中的所有角色名称
    
    返回:
        List[str]: 角色名称列表
    """
    characters = set()
    for turn in chat_history:
        if turn.role == "assistant" and turn.speaker_mapping:
            characters.add(turn.speaker_mapping)
    
    return list(characters)


def _get_last_psychological_state(app_state, character_id: str) -> Optional[dict]:
    """
    获取角色的上一个心理状态
    
    参数:
        app_state: AppState
                应用状态
        character_id: str
                角色ID
    
    返回:
        Optional[dict]: 上一个心理状态
    """
    if character_id not in app_state.psychological_state_history:
        return None
    
    states = app_state.psychological_state_history[character_id]
    if states:
        return states[-1]
    
    return None


async def _store_psychological_state(graphiti_service, state: dict, session_id: str):
    """
    存储心理状态到Graphiti
    
    参数:
        graphiti_service: Graphiti服务
        state: 心理状态字典
        session_id: 会话ID
    
    TODO: 实现Graphiti存储逻辑
    """
    # 将心理状态作为Episode存储
    episode_name = f"Psychological State - {state['character_id']}"
    episode_body = f"Role: {state['character_id']}, Dominant Emotion: {state['dominant_emotion']}, Stability: {state['stability_score']}"
    
    try:
        result = await graphiti_service.graphiti.add_episode(
            name=episode_name,
            episode_body=episode_body,
            source="text",
            source_description="psychological_state",
            reference_time=state.get('observed_at', datetime.now()),
            group_id=session_id
        )
        logger.debug(f"心理状态存储成功 - UUID: {result.uuid}")
    except Exception as e:
        logger.error(f"存储心理状态时出错: {e}")


def _optimize_context(
    original_messages: list,
    parsed_content,
    memories: list
) -> list:
    """
    优化上下文
    
    参数:
        original_messages: list
                原始消息列表
        parsed_content: ParsedContent
                解析后的内容
        memories: list
                检索到的记忆
    
    返回:
        list: 优化后的消息列表
    
    策略：
        - 保留所有指令性内容（完整）
        - 用Graphiti召回的相关记忆替换部分叙事性内容
        - 保留最近N轮对话历史
        - Token优化
    """
    # 步骤1: 构建记忆摘要
    memory_summary = "\n".join([
        f"- {mem['fact']}" for mem in memories[:5]
    ])
    
    # 步骤2: 构建增强的系统消息
    enhanced_system = ""
    if parsed_content.instructions:
        enhanced_system = parsed_content.instructions[0].content
    
    if memories:
        enhanced_system += "\n\n相关记忆：\n" + memory_summary
    
    # 步骤3: 构建优化后的消息
    optimized = []
    
    # 添加系统消息
    if enhanced_system:
        optimized.append({"role": "system", "content": enhanced_system})
    
    # 添加对话历史（保留最近5轮）
    recent_dialogs = parsed_content.chat_history[-5:]
    for dialog in recent_dialogs:
        optimized.append({
            "role": dialog.role.lower(),
            "content": dialog.content
        })
    
    # 添加最后一个user消息
    optimized.append(original_messages[-1])
    
    return optimized


def _format_chat_completion_response(
    completion_response: dict,
    model: str,
    memories_count: int
) -> ChatCompletionResponse:
    """
    格式化为OpenAI兼容响应
    
    参数:
        completion_response: dict
                LLM原始响应
        model: str
                模型名称
        memories_count: int
                检索的记忆数量
    
    返回:
        ChatCompletionResponse: 格式化的响应
    """
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4()}",
        object="chat.completion",
        created=int(datetime.now().timestamp()),
        model=model,
        choices=[{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": completion_response['content']
            },
            "finish_reason": completion_response.get('finish_reason', 'stop')
        }],
        usage={
            "prompt_tokens": completion_response.get('prompt_tokens', 0),
            "completion_tokens": completion_response.get('completion_tokens', 0),
            "total_tokens": completion_response.get('total_tokens', 0)
        },
        extra={
            "memories_used": memories_count
        }
    )


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 启动应用
if __name__ == "__main__":
    import uvicorn
    config = load_app_config()
    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
        log_level=config.api.log_level
    )
