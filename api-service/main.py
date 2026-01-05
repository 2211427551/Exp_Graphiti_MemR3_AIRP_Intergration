# ============================================
# FastAPI主应用入口
# ============================================
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import uuid
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入配置和服务
from config.settings import load_app_config
from config.graphiti_config import GraphitiClientFactory
from services.parser_service import SillyTavernParser
from services.graphiti_service import GraphitiService
from services.llm_service import LLMService
from models.requests import ChatCompletionRequest
from models.responses import ChatCompletionResponse, HealthResponse

# 全局变量
graphiti_service: GraphitiService = None
llm_service: LLMService = None
parser_service: SillyTavernParser = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    
    参数:
        app: FastAPI
                FastAPI应用实例
    
    功能:
        启动时：初始化所有服务
        关闭时：清理所有资源
    
    流程:
        启动阶段：
            1. 加载应用配置
            2. 初始化Graphiti客户端
            3. 初始化Graphiti服务
            4. 初始化LLM服务
            5. 初始化解析器服务
        
        关闭阶段：
            1. 关闭Graphiti客户端
            2. 清理资源
    """
    global graphiti_service, llm_service, parser_service
    
    # 启动阶段
    logger.info("=" * 60)
    logger.info("AIRP记忆系统启动中...")
    logger.info("=" * 60)
    
    # 步骤1: 加载配置
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
    
    # 存储到app状态
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
    description="基于Graphiti的记忆增强系统，为SillyTavern提供OpenAI兼容API",
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


# 健康检查端点
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查端点
    
    返回:
        HealthResponse: 健康状态
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )


# OpenAI兼容端点
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest
):
    """
    OpenAI兼容的Chat Completions端点
    
    参数:
        request: Request
                FastAPI请求对象（用于提取header）
        
        body: ChatCompletionRequest
                请求体（包含messages, model等）
    
    返回:
        ChatCompletionResponse: OpenAI兼容的响应
    
    流程:
        1. 提取session_id
           a. 从header: X-Session-ID
           b. 从请求参数: session_id
           c. 从系统消息: 解析SESSION_ID
        
        2. 提取最后一个user消息
           a. 从messages数组中提取
           b. 这通常是包含完整上下文的提示词
        
        3. 解析SillyTavern格式
           a. 调用parser_service.parse()
           b. 得到结构化内容
        
        4. 记忆处理（异步）
           a. 对于叙事性内容，调用graphiti_service.add_episode()
           b. 实体关系提取
           c. 去重和合并
           d. 存储到知识图谱
        
        5. 记忆检索
           a. 调用graphiti_service.search()
           b. 检索相关记忆
        
        6. 上下文优化
           a. 构建增强的提示词
           b. 保留指令性内容（完整）
           c. 用检索的记忆替换部分叙事性内容
           d. Token优化
        
        7. LLM调用
           a. 调用llm_service.generate_completion()
           b. 传递优化后的消息
        
        8. 响应后处理
           a. 从LLM响应中提取新信息
           b. 存储到Graphiti（异步）
           c. 格式化为OpenAI兼容响应
    
    异常:
        HTTPException: API错误
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
    
    # 步骤4: 记忆处理（异步）
    await graphiti_svc.process_content(
        session_id=session_id,
        parsed_content=parsed_content
    )
    
    # 步骤5: 记忆检索
    related_memories = await graphiti_svc.search_memories(
        session_id=session_id,
        query=last_user_message.content,
        limit=10
    )
    logger.info(f"检索到 {len(related_memories)} 条相关记忆")
    
    # 步骤6: 上下文优化
    optimized_messages = _optimize_context(
        original_messages=body.messages,
        parsed_content=parsed_content,
        memories=related_memories
    )
    logger.debug(f"优化后消息数: {len(optimized_messages)}")
    
    # 步骤7: LLM调用
    completion_response = await llm_svc.generate_completion(
        model=body.model,
        messages=optimized_messages,
        temperature=body.temperature,
        max_tokens=body.max_tokens
    )
    logger.info(f"LLM响应完成 - tokens: {completion_response['total_tokens']}")
    
    # 步骤8: 响应后处理（异步）
    asyncio.create_task(
        graphiti_svc.process_response(
            session_id=session_id,
            response_content=completion_response['content']
        )
    )
    
    # 步骤9: 返回OpenAI兼容响应
    return _format_chat_completion_response(
        completion_response=completion_response,
        model=body.model,
        memories_count=len(related_memories)
    )


def _extract_session_id(request: Request, body: ChatCompletionRequest) -> str:
    """
    提取会话ID
    
    参数:
        request: Request
                FastAPI请求对象
        body: ChatCompletionRequest
                请求体
    
    返回:
        str: 会话ID
    
    优先级:
        1. 自定义header: X-Session-ID
        2. 请求参数: session_id
        3. 系统消息内容
    """
    # 方式1: 自定义header
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        return session_id
    
    # 方式2: 请求参数（如果body扩展支持）
    if hasattr(body, 'session_id') and body.session_id:
        return body.session_id
    
    # 方式3: 解析系统消息
    for message in body.messages:
        if message.role == "system":
            if "SESSION_ID:" in message.content:
                return message.content.split("SESSION_ID:")[1].strip()
    
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
    """
    for message in reversed(messages):
        if message.role == "user":
            return message
    
    raise HTTPException(status_code=400, detail="No user message found")


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
    
    策略:
        - 保留所有指令性内容（完整）
        - 用Graphiti召回的相关记忆替换部分叙事性内容
        - 保留最近N轮对话历史
        - Token优化
    """
    # 步骤1: 构建记忆摘要
    memory_summary = "\n\n".join([
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
    
    if enhanced_system:
        optimized.append({"role": "system", "content": enhanced_system})
    
    # 步骤4: 保留最近5轮对话
    recent_dialogs = parsed_content.chat_history[-5:]
    for dialog in recent_dialogs:
        optimized.append({
            "role": dialog.role.lower(),
            "content": dialog.content
        })
    
    # 步骤5: 添加最后一个user消息
    optimized.append({"role": "user", "content": original_messages[-1].content})
    
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
