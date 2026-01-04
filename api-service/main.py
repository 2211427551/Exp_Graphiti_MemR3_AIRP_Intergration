from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
import os
from datetime import datetime

# 配置日志
import sys

# 检查是否在容器中运行
def is_in_container():
    import os
    # 检查常见的容器环境变量
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

log_file_path = '/app/logs/airp-memory-system.log' if is_in_container() else './logs/airp-memory-system.log'

# 确保日志目录存在
import os
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AIRP Memory System API",
    description="Enhanced memory system for SillyTavern with Graphiti integration",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
class Config:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    
    # 检查是否为演示模式
    @staticmethod
    def is_demo_mode():
        return Config.DEEPSEEK_API_KEY in ["", "test_key_for_demo_mode"]
    
    @staticmethod
    def get_temporal_config():
        """获取双时序模型配置"""
        return {
            "migration_phase": os.getenv("TEMPORAL_MIGRATION_PHASE", "phase1"),
            "model_version": os.getenv("TEMPORAL_MODEL_VERSION", "1.0"),
            "optimistic_lock_retry_count": int(os.getenv("TEMPORAL_OPTIMISTIC_LOCK_RETRY_COUNT", "3")),
            "optimistic_lock_retry_delay_ms": int(os.getenv("TEMPORAL_OPTIMISTIC_LOCK_RETRY_DELAY_MS", "100")),
            "query_cache_size": int(os.getenv("TEMPORAL_QUERY_CACHE_SIZE", "100")),
            "query_cache_ttl": int(os.getenv("TEMPORAL_QUERY_CACHE_TTL", "60"))
        }

# 初始化增强Graphiti服务
def init_enhanced_graphiti_service():
    """初始化增强Graphiti服务"""
    try:
        from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService
        return EnhancedGraphitiService()
    except ImportError as e:
        logger.warning(f"无法导入EnhancedGraphitiService: {str(e)}，将使用基础服务")
        # 回退到基础服务
        from api_service.services.graphiti_service import GraphitiService
        return GraphitiService()
    except Exception as e:
        logger.error(f"初始化Graphiti服务失败: {str(e)}")
        return None

# 创建全局服务实例
enhanced_graphiti_service = init_enhanced_graphiti_service()

# SillyTavern标签解析函数
def parse_sillytavern_tags(text: str) -> Dict[str, Any]:
    """解析SillyTavern标签格式，提取实体和关系"""
    import re
    
    result = {
        "characters": [],
        "locations": [],
        "actions": [],
        "emotions": [],
        "raw_text": text
    }
    
    # 简单的正则表达式匹配常见标签格式
    # 例如: {{char}}, {{user}}, [[location]], *action*, (emotion)
    character_pattern = r'\{\{(\w+)\}\}'
    location_pattern = r'\[\[([^\]]+)\]\]'
    action_pattern = r'\*([^*]+)\*'
    emotion_pattern = r'\(([^)]+)\)'
    
    # 提取匹配项
    result["characters"] = re.findall(character_pattern, text)
    result["locations"] = re.findall(location_pattern, text)
    result["actions"] = re.findall(action_pattern, text)
    result["emotions"] = re.findall(emotion_pattern, text)
    
    logger.info(f"解析SillyTavern标签: 字符={result['characters']}, 地点={result['locations']}, 动作={result['actions']}, 情绪={result['emotions']}")
    
    return result

# 生成模拟响应
def generate_mock_response(messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
    """为演示模式生成模拟响应"""
    last_message = messages[-1]["content"] if messages else "你好！"
    
    # 解析标签
    parsed_tags = parse_sillytavern_tags(last_message)
    
    # 基于解析结果生成响应
    if parsed_tags["characters"]:
        response_text = f"我正在与 {', '.join(parsed_tags['characters'])} 进行对话"
        if parsed_tags["locations"]:
            response_text += f"，地点在 {', '.join(parsed_tags['locations'])}"
        if parsed_tags["actions"]:
            response_text += f"。我看到动作: {', '.join(parsed_tags['actions'])}"
        response_text += "。这是一个增强的记忆系统演示。"
    else:
        response_text = f"你好！我收到了你的消息: '{last_message[:100]}...'。这是一个AIRP记忆系统的演示响应。"
    
    return {
        "id": f"chatcmpl-mock-{os.urandom(4).hex()}",
        "object": "chat.completion",
        "created": int(os.path.getctime(__file__)),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(str(messages)),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(str(messages)) + len(response_text.split())
        }
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "service": "AIRP Memory System",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "AIRP Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# OpenAI兼容端点
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI兼容的聊天补全端点
    接收SillyTavern请求并返回增强的响应
    """
    try:
        # 解析请求
        request_data = await request.json()
        logger.info(f"收到聊天请求: {json.dumps(request_data, ensure_ascii=False)[:500]}...")
        
        # 验证请求
        if "messages" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'messages'字段")
        
        # 获取模型名称
        model = request_data.get("model", "deepseek-v3.2")
        
        # 处理输入（这里将是主要的业务逻辑）
        # 1. 解析SillyTavern输入格式
        # 2. 提取实体和关系
        # 3. 存储到Graphiti
        # 4. 检索相关记忆
        # 5. 增强上下文
        # 6. 调用DeepSeek API或生成模拟响应
        
        messages = request_data.get("messages", [])
        
        # 检查是否为演示模式
        if Config.is_demo_mode():
            logger.info("运行在演示模式，生成模拟响应")
            return generate_mock_response(messages, model)
        else:
            # 真实模式：调用DeepSeek API
            # 构建DeepSeek API请求
            deepseek_request = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": request_data.get("temperature", 0.7),
                "max_tokens": request_data.get("max_tokens", 2000),
                "stream": False
            }
            
            # 调用DeepSeek API
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                try:
                    response = await client.post(
                        f"{Config.DEEPSEEK_BASE_URL}/chat/completions",
                        json=deepseek_request,
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"DeepSeek API错误: {response.status_code} - {response.text}")
                        raise HTTPException(status_code=response.status_code, detail=response.text)
                    
                    deepseek_response = response.json()
                    
                    # 返回OpenAI兼容格式
                    return {
                        "id": f"chatcmpl-{os.urandom(8).hex()}",
                        "object": "chat.completion",
                        "created": int(os.path.getctime(__file__)),
                        "model": model,
                        "choices": deepseek_response.get("choices", []),
                        "usage": deepseek_response.get("usage", {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        })
                    }
                    
                except httpx.TimeoutException:
                    logger.error("DeepSeek API请求超时")
                    raise HTTPException(status_code=504, detail="DeepSeek API请求超时")
                except httpx.RequestError as e:
                    logger.error(f"DeepSeek API请求错误: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"DeepSeek API请求错误: {str(e)}")
    
    except json.JSONDecodeError:
        logger.error("无效的JSON请求")
        raise HTTPException(status_code=400, detail="无效的JSON请求")
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

# 会话管理端点
@app.post("/v1/sessions")
async def create_session(request: Request):
    """创建新会话"""
    try:
        request_data = await request.json()
        session_id = request_data.get("session_id", f"sess-{os.urandom(8).hex()}")
        
        # 这里将实现会话创建逻辑
        # 包括在Graphiti中初始化会话空间
        
        return {
            "session_id": session_id,
            "status": "created",
            "timestamp": int(os.path.getctime(__file__))
        }
    
    except Exception as e:
        logger.error(f"创建会话错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建会话错误: {str(e)}")

@app.get("/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话信息"""
    # 这里将实现会话信息检索逻辑
    return {
        "session_id": session_id,
        "status": "active",
        "entities_count": 0,  # 待实现
        "relationships_count": 0,  # 待实现
        "last_updated": int(os.path.getctime(__file__))
    }

# 监控端点
@app.get("/metrics")
async def get_metrics():
    """获取系统指标"""
    return {
        "system_status": "healthy",
        "memory_usage": "N/A",  # 待实现
        "cpu_usage": "N/A",  # 待实现
        "active_sessions": 0,  # 待实现
        "total_entities": 0,  # 待实现
        "requests_per_minute": 0  # 待实现
    }

# ========== 双时序API端点 ==========

@app.get("/v1/temporal/config")
async def get_temporal_config():
    """获取双时序模型配置"""
    try:
        return {
            "success": True,
            "config": Config.get_temporal_config(),
            "service_available": enhanced_graphiti_service is not None
        }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@app.post("/v1/temporal/entities")
async def create_temporal_entity(request: Request):
    """创建双时序实体"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        # 必填字段验证
        if "session_id" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'session_id'字段")
        if "entity_data" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'entity_data'字段")
        
        session_id = request_data["session_id"]
        entity_data = request_data["entity_data"]
        valid_from = request_data.get("valid_from")
        valid_until = request_data.get("valid_until")
        created_by = request_data.get("created_by")
        
        entity_id = enhanced_graphiti_service.create_entity_bitemporal(
            session_id=session_id,
            entity_data=entity_data,
            valid_from=valid_from,
            valid_until=valid_until,
            created_by=created_by
        )
        
        if not entity_id:
            raise HTTPException(status_code=500, detail="创建实体失败")
        
        return {
            "success": True,
            "entity_id": entity_id,
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建实体失败: {str(e)}")

@app.get("/v1/temporal/entities/{entity_id}")
async def get_entity_at_time(session_id: str, entity_id: str, query_time: Optional[str] = None):
    """获取实体在指定时间点的状态"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        # 如果未提供查询时间，使用当前时间
        if not query_time:
            from datetime import datetime
            query_time = datetime.now().isoformat()
        
        entity_data = enhanced_graphiti_service.get_entity_at_time(
            session_id=session_id,
            entity_id=entity_id,
            query_time=query_time
        )
        
        if not entity_data:
            raise HTTPException(status_code=404, detail="实体不存在或指定时间点无效")
        
        return {
            "success": True,
            "entity": entity_data,
            "query_time": query_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实体失败: {str(e)}")

@app.get("/v1/temporal/entities/{entity_id}/history")
async def get_entity_history(session_id: str, entity_id: str, 
                            start_time: Optional[str] = None, 
                            end_time: Optional[str] = None):
    """获取实体的历史版本记录"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        time_range = None
        if start_time or end_time:
            time_range = (start_time, end_time)
        
        history = enhanced_graphiti_service.get_entity_history(
            session_id=session_id,
            entity_id=entity_id,
            time_range=time_range
        )
        
        return {
            "success": True,
            "entity_id": entity_id,
            "history": history,
            "count": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")

@app.put("/v1/temporal/entities/{entity_id}")
async def update_temporal_entity(request: Request, entity_id: str):
    """双时序版本化更新实体"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        if "session_id" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'session_id'字段")
        if "updates" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'updates'字段")
        
        session_id = request_data["session_id"]
        updates = request_data["updates"]
        valid_from = request_data.get("valid_from")
        valid_until = request_data.get("valid_until")
        updated_by = request_data.get("updated_by")
        
        new_entity_id = enhanced_graphiti_service.update_entity_bitemporal(
            session_id=session_id,
            entity_id=entity_id,
            updates=updates,
            valid_from=valid_from,
            valid_until=valid_until,
            updated_by=updated_by
        )
        
        if not new_entity_id:
            raise HTTPException(status_code=500, detail="更新实体失败")
        
        return {
            "success": True,
            "old_entity_id": entity_id,
            "new_entity_id": new_entity_id,
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新实体失败: {str(e)}")

@app.post("/v1/temporal/relationships")
async def create_temporal_relationship(request: Request):
    """创建双时序关系"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        # 必填字段验证
        required_fields = ["session_id", "source_entity_id", "target_entity_id", 
                          "relation_type", "properties"]
        for field in required_fields:
            if field not in request_data:
                raise HTTPException(status_code=400, detail=f"缺少'{field}'字段")
        
        relationship_id = enhanced_graphiti_service.create_relationship_bitemporal(
            session_id=request_data["session_id"],
            source_entity_id=request_data["source_entity_id"],
            target_entity_id=request_data["target_entity_id"],
            relation_type=request_data["relation_type"],
            properties=request_data["properties"],
            valid_from=request_data.get("valid_from"),
            valid_until=request_data.get("valid_until"),
            relation_subtype=request_data.get("relation_subtype"),
            confidence=request_data.get("confidence"),
            direction=request_data.get("direction", "outgoing"),
            created_by=request_data.get("created_by")
        )
        
        if not relationship_id:
            raise HTTPException(status_code=500, detail="创建关系失败")
        
        return {
            "success": True,
            "relationship_id": relationship_id,
            "session_id": request_data["session_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建关系失败: {str(e)}")

@app.get("/v1/temporal/relationships")
async def get_temporal_relationships(session_id: str, entity_id: str, 
                                    query_time: Optional[str] = None,
                                    relation_types: Optional[str] = None,
                                    direction: str = "both"):
    """获取实体在指定时间点的关系"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        # 如果未提供查询时间，使用当前时间
        if not query_time:
            from datetime import datetime
            query_time = datetime.now().isoformat()
        
        # 解析关系类型列表
        relation_types_list = None
        if relation_types:
            relation_types_list = relation_types.split(",")
        
        relationships = enhanced_graphiti_service.get_relationships_at_time(
            session_id=session_id,
            entity_id=entity_id,
            query_time=query_time,
            relation_types=relation_types_list,
            direction=direction
        )
        
        return {
            "success": True,
            "entity_id": entity_id,
            "query_time": query_time,
            "relationships": relationships,
            "count": len(relationships)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取关系失败: {str(e)}")

@app.get("/v1/temporal/relationships/timeline")
async def get_relationship_timeline(session_id: str, 
                                   source_entity_id: str, 
                                   target_entity_id: str,
                                   relation_type: str):
    """获取关系的完整时间线"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        timeline = enhanced_graphiti_service.get_relationship_timeline(
            session_id=session_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type
        )
        
        return {
            "success": True,
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "relation_type": relation_type,
            "timeline": timeline,
            "count": len(timeline)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取时间线失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取时间线失败: {str(e)}")

@app.get("/v1/temporal/valid-entities")
async def query_valid_entities(session_id: str, query_time: Optional[str] = None,
                              entity_type: Optional[str] = None,
                              limit: int = 100):
    """查询在指定时间点有效的实体"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        # 如果未提供查询时间，使用当前时间
        if not query_time:
            from datetime import datetime
            query_time = datetime.now().isoformat()
        
        entities = enhanced_graphiti_service.query_valid_at_time(
            session_id=session_id,
            query_time=query_time,
            entity_type=entity_type,
            limit=limit
        )
        
        return {
            "success": True,
            "query_time": query_time,
            "entity_type": entity_type,
            "entities": entities,
            "count": len(entities)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询有效实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询有效实体失败: {str(e)}")

@app.get("/v1/temporal/service-info")
async def get_temporal_service_info():
    """获取增强Graphiti服务信息"""
    try:
        if not enhanced_graphiti_service:
            return {
                "success": False,
                "message": "服务不可用",
                "available": False
            }
        
        service_info = enhanced_graphiti_service.get_service_info()
        
        return {
            "success": True,
            "service_info": service_info,
            "available": True
        }
        
    except Exception as e:
        logger.error(f"获取服务信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取服务信息失败: {str(e)}")

# ========== 高级功能API端点 ==========

@app.get("/v1/advanced/services-info")
async def get_advanced_services_info():
    """获取高级功能服务信息"""
    try:
        if not enhanced_graphiti_service:
            return {
                "success": False,
                "error": "Graphiti服务不可用"
            }
        
        service_info = enhanced_graphiti_service.get_advanced_service_stats()
        
        return {
            "success": True,
            "services": service_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取高级服务信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取高级服务信息失败: {str(e)}")

@app.post("/v1/pattern/detect")
async def detect_patterns(request: Request):
    """检测会话中的模式"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        if "session_id" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'session_id'字段")
        
        session_id = request_data["session_id"]
        pattern_types = request_data.get("pattern_types", ["sequential", "causal", "clustering"])
        min_confidence = request_data.get("min_confidence", 0.7)
        min_support = request_data.get("min_support", 3)
        
        result = enhanced_graphiti_service.pattern_detection_service.detect_patterns(
            session_id=session_id,
            pattern_types=pattern_types,
            min_confidence=min_confidence,
            min_support=min_support
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "patterns_detected": result
        }
        
    except Exception as e:
        logger.error(f"模式检测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"模式检测失败: {str(e)}")

@app.get("/v1/pattern/anomalies/{session_id}")
async def detect_anomalies(session_id: str, 
                          threshold: float = 0.8,
                          time_window: Optional[str] = None):
    """检测会话中的异常"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        result = enhanced_graphiti_service.pattern_detection_service.detect_anomalies(
            session_id=session_id,
            threshold=threshold,
            time_window=time_window
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "anomalies_detected": result
        }
        
    except Exception as e:
        logger.error(f"异常检测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"异常检测失败: {str(e)}")

@app.post("/v1/causal/discover")
async def discover_causal_relationships(request: Request):
    """发现因果关系"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        if "session_id" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'session_id'字段")
        
        session_id = request_data["session_id"]
        time_window = request_data.get("time_window")
        min_confidence = request_data.get("min_confidence", 0.7)
        min_support = request_data.get("min_support", 2)
        
        result = enhanced_graphiti_service.causal_inference_service.discover_causal_relationships(
            session_id=session_id,
            time_window=time_window,
            min_confidence=min_confidence,
            min_support=min_support
        )
        
        return result
        
    except Exception as e:
        logger.error(f"因果关系发现失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"因果关系发现失败: {str(e)}")

@app.get("/v1/causal/paths/{session_id}")
async def get_causal_paths(session_id: str, 
                          source_entity_id: str,
                          target_entity_id: str,
                          max_path_length: int = 5):
    """获取因果路径"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        paths = enhanced_graphiti_service.causal_inference_service.get_causal_paths(
            session_id=session_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            max_path_length=max_path_length
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "paths": paths
        }
        
    except Exception as e:
        logger.error(f"获取因果路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取因果路径失败: {str(e)}")

@app.post("/v1/causal/predict-intervention")
async def predict_intervention_effect(request: Request):
    """预测干预效果"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        required_fields = ["session_id", "intervention_entity_id", 
                          "intervention_changes", "target_entity_id"]
        for field in required_fields:
            if field not in request_data:
                raise HTTPException(status_code=400, detail=f"缺少'{field}'字段")
        
        result = enhanced_graphiti_service.causal_inference_service.predict_intervention_effect(
            session_id=request_data["session_id"],
            intervention_entity_id=request_data["intervention_entity_id"],
            intervention_changes=request_data["intervention_changes"],
            target_entity_id=request_data["target_entity_id"],
            confidence_threshold=request_data.get("confidence_threshold", 0.6)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"干预效果预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"干预效果预测失败: {str(e)}")

@app.get("/v1/dashboard/metrics/{session_id}")
async def get_dashboard_metrics(session_id: str,
                               time_window: Optional[str] = None):
    """获取看板指标"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        metrics = enhanced_graphiti_service.realtime_dashboard_service.get_dashboard_metrics(
            session_id=session_id,
            time_window=time_window
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"获取看板指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取看板指标失败: {str(e)}")

@app.get("/v1/dashboard/trends/{session_id}")
async def get_dashboard_trends(session_id: str,
                               trend_type: str = "entity_growth",
                               time_points: int = 10):
    """获取看板趋势"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        trends = enhanced_graphiti_service.realtime_dashboard_service.get_trends(
            session_id=session_id,
            trend_type=trend_type,
            time_points=time_points
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "trends": trends
        }
        
    except Exception as e:
        logger.error(f"获取看板趋势失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取看板趋势失败: {str(e)}")

@app.post("/v1/batch/import")
async def batch_import_data(request: Request):
    """批量导入数据"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        request_data = await request.json()
        
        if "session_id" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'session_id'字段")
        if "data_type" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'data_type'字段")
        if "data" not in request_data:
            raise HTTPException(status_code=400, detail="缺少'data'字段")
        
        session_id = request_data["session_id"]
        data_type = request_data["data_type"]
        data = request_data["data"]
        
        result = enhanced_graphiti_service.batch_import_export_service.batch_import(
            session_id=session_id,
            data_type=data_type,
            data=data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"批量导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量导入失败: {str(e)}")

@app.get("/v1/batch/export/{session_id}")
async def batch_export_data(session_id: str,
                            export_format: str = "json",
                            include_history: bool = True):
    """批量导出数据"""
    try:
        if not enhanced_graphiti_service:
            raise HTTPException(status_code=503, detail="Graphiti服务不可用")
        
        result = enhanced_graphiti_service.batch_import_export_service.batch_export(
            session_id=session_id,
            export_format=export_format,
            include_history=include_history
        )
        
        return result
        
    except Exception as e:
        logger.error(f"批量导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量导出失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8001))  # 默认为8001以避免与SillyTavern冲突
    uvicorn.run(app, host="0.0.0.0", port=port)
