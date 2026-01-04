"""
FastAPI应用主入口

AIRP Knowledge Graph API - 基于graphiti_core的双时序知识图谱API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

# 导入路由
from api_service.api.routes import health_router, episodes_router, search_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 全局服务实例
enhanced_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 声明全局变量（必须在任何使用之前）
    global enhanced_service
    
    # 启动时初始化
    logger.info("🚀 启动AIRP Knowledge Graph API...")
    
    from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService
    
    try:
        enhanced_service = EnhancedGraphitiService()
        logger.info("✅ EnhancedGraphitiService初始化完成")
        
        # 检查graphiti_core状态
        if enhanced_service.is_graphiti_core_enabled():
            info = enhanced_service.get_graphiti_core_info()
            logger.info(f"✅ graphiti_core已启用 (版本: {info.get('version', 'unknown')})")
            logger.info(f"📦 可用功能: {', '.join(info.get('features', []))}")
        else:
            logger.warning("⚠️  graphiti_core未启用，请检查Neo4j连接和配置")
        
    except Exception as e:
        logger.error(f"❌ 初始化EnhancedGraphitiService失败: {str(e)}")
        logger.warning("⚠️  API将在服务未初始化的情况下运行")
    
    yield
    
    # 关闭时清理
    logger.info("🛑 关闭AIRP Knowledge Graph API...")
    
    if enhanced_service:
        try:
            enhanced_service.close()
            logger.info("✅ EnhancedGraphitiService已关闭")
        except Exception as e:
            logger.error(f"⚠️  关闭服务时出错: {str(e)}")
        finally:
            enhanced_service = None
    
    logger.info("✅ API已安全关闭")


# 创建FastAPI应用
app = FastAPI(
    title="AIRP Knowledge Graph API",
    description="基于graphiti_core的双时序知识图谱REST API，支持语义搜索、时间旅行查询和混合检索",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(health_router)
app.include_router(episodes_router)
app.include_router(search_router)


if __name__ == "__main__":
    import uvicorn
    
    # 从环境变量获取配置
    host = "0.0.0.0"
    port = 8000
    workers = 1
    
    logger.info(f"🌐 启动API服务器: http://{host}:{port}")
    logger.info(f"� API文档: http://{host}:{port}/docs")
    
    uvicorn.run(
        "api_service.api.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info"
    )
