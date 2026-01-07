# ============================================
# Graphiti客户端配置模块
# ============================================
from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from neo4j import GraphDatabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GraphitiClientFactory:
    """Graphiti客户端工厂类"""
    
    @staticmethod
    async def create_graphiti_client(
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        deepseek_api_key: str,
        deepseek_base_url: str,
        deepseek_model: str,
        deepseek_small_model: str,
        siliconflow_api_key: str,
        siliconflow_base_url: str,
        siliconflow_embedding_model: str,
        siliconflow_embedding_dim: int,
        siliconflow_reranker_model: str,
        enable_cross_encoder: bool = True,
        semaphore_limit: int = 5
    ) -> Graphiti:
        """
        创建Graphiti客户端实例
        
        参数:
            neo4j_uri: str
                Neo4j连接URI，格式：bolt://host:port
            
            neo4j_user: str
                Neo4j用户名
            
            neo4j_password: str
                Neo4j密码
            
            deepseek_api_key: str
                DeepSeek API密钥
            
            deepseek_base_url: str
                DeepSeek API基础URL
                标准端点：https://api.deepseek.com
                Beta端点：https://api.deepseek.com/beta（推荐）
            
            deepseek_model: str
                DeepSeek主模型名称，如：deepseek-chat
            
            deepseek_small_model: str
                DeepSeek小模型名称
            
            siliconflow_api_key: str
                硅基流动API密钥
            
            siliconflow_base_url: str
                硅基流动API基础URL，如：https://api.siliconflow.cn/v1
            
            siliconflow_embedding_model: str
                硅基流动嵌入模型名称，如：BAAI/bge-m3
            
            siliconflow_embedding_dim: int
                嵌入向量维度，如：1024
            
            siliconflow_reranker_model: str
                硅基流动重排序模型名称，如：BAAI/bge-reranker-v2-m3
            
            enable_cross_encoder: bool = True
                是否启用Cross-Encoder（重排序器），提升检索质量
            
            semaphore_limit: int = 5
                Graphiti并发限制，避免API限流
        
        返回:
            Graphiti: 初始化完成的Graphiti实例
        
        流程:
            1. 验证Neo4j连接
            2. 创建DeepSeek LLM客户端（使用OpenAIGenericClient）
            3. 创建硅基流动Embedding客户端（使用OpenAIEmbedder）
            4. 初始化Graphiti实例
            5. 构建索引和约束
            6. 返回Graphiti实例
        
        异常:
            ConnectionError: 数据库连接失败
            AuthenticationError: 认证失败
            ConfigurationError: 配置错误
        """
        logger.info(f"初始化Graphiti客户端 - Neo4j URI: {neo4j_uri}")
        
        try:
            # 步骤1: 验证Neo4j连接
            logger.info("验证Neo4j连接...")
            driver = GraphDatabase.driver(
                uri=neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            driver.verify_connectivity()
            logger.info("Neo4j连接验证成功")
            
            # 步骤2: 创建DeepSeek LLM客户端
            # 使用OpenAIGenericClient，因为它支持自定义base_url和Strict模式
            logger.info(f"创建DeepSeek LLM客户端 - Base URL: {deepseek_base_url}")
            llm_config = LLMConfig(
                api_key=deepseek_api_key,
                model=deepseek_model,
                small_model=deepseek_small_model,
                base_url=deepseek_base_url
            )
            llm_client = OpenAIGenericClient(config=llm_config)
            logger.info("DeepSeek LLM客户端创建成功")
            
            # 步骤3: 创建硅基流动Embedding客户端
            # 硅基流动的Embedding API是OpenAI兼容的
            logger.info(f"创建硅基流动Embedding客户端 - 模型: {siliconflow_embedding_model}")
            embedder_config = OpenAIEmbedderConfig(
                api_key=siliconflow_api_key,
                embedding_model=siliconflow_embedding_model,
                embedding_dim=siliconflow_embedding_dim,
                base_url=siliconflow_base_url
            )
            embedder = OpenAIEmbedder(config=embedder_config)
            logger.info("硅基流动Embedding客户端创建成功")
            
            # 步骤4: 创建Cross-Encoder（可选，提升检索质量）
            cross_encoder = None
            if enable_cross_encoder:
                logger.info(f"创建Cross-Encoder客户端 - 模型: {siliconflow_reranker_model}")
                reranker_config = LLMConfig(
                    api_key=siliconflow_api_key,
                    model=siliconflow_reranker_model,
                    base_url=siliconflow_base_url
                )
                cross_encoder = OpenAIRerankerClient(
                    client=llm_client,
                    config=reranker_config
                )
                logger.info("Cross-Encoder客户端创建成功")
            
            # 步骤5: 初始化Graphiti实例
            logger.info("初始化Graphiti实例...")
            graphiti = Graphiti(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=cross_encoder,
                semaphore_limit=semaphore_limit
            )
            logger.info("Graphiti实例初始化成功")
            
            # 步骤6: 构建索引和约束
            logger.info("构建Neo4j索引和约束...")
            await graphiti.build_indices_and_constraints()
            logger.info("索引和约束构建完成")
            
            # 步骤7: 验证Cross-Encoder（如果启用）
            if enable_cross_encoder and cross_encoder is not None:
                logger.info("Cross-Encoder已启用，将提升检索质量")
            else:
                logger.info("Cross-Encoder未启用，使用默认检索模式")
            
            return graphiti
            
        except Exception as e:
            logger.error(f"Graphiti初始化失败: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def close_graphiti_client(graphiti: Graphiti) -> None:
        """
        关闭Graphiti客户端
        
        参数:
            graphiti: Graphiti
                要关闭的Graphiti实例
        
        流程:
            1. 关闭Neo4j驱动连接
            2. 清理资源
        
        异常:
            Exception: 关闭过程中的异常
        """
        logger.info("关闭Graphiti客户端...")
        try:
            await graphiti.close()
            logger.info("Graphiti客户端关闭成功")
        except Exception as e:
            logger.error(f"关闭Graphiti客户端时出错: {e}", exc_info=True)
