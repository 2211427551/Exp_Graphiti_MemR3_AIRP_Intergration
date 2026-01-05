# ============================================
# 配置模块
# ============================================
from pydantic_settings import BaseSettings, Field
from typing import Optional
import os


class Neo4jConfig(BaseSettings):
    """Neo4j配置类"""
    
    # 参数定义
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j Bolt协议连接URI"
    )
    
    user: str = Field(
        default="neo4j",
        description="Neo4j用户名"
    )
    
    password: str = Field(
        ...,
        description="Neo4j密码（必填）"
    )
    
    class Config:
        env_prefix = "NEO4J_"
        case_sensitive = False


class DeepSeekConfig(BaseSettings):
    """DeepSeek LLM配置类"""
    
    # 参数定义
    api_key: str = Field(
        ...,
        description="DeepSeek API密钥（必填）"
    )
    
    base_url: str = Field(
        default="https://api.deepseek.com/beta",
        description="DeepSeek API基础URL，默认使用beta端点支持Strict模式"
    )
    
    model: str = Field(
        default="deepseek-chat",
        description="DeepSeek模型名称"
    )
    
    small_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek小模型名称（用于简单任务）"
    )
    
    class Config:
        env_prefix = "DEEPSEEK_"
        case_sensitive = False


class SiliconFlowConfig(BaseSettings):
    """硅基流动API配置类"""
    
    # 参数定义
    api_key: str = Field(
        ...,
        description="硅基流动API密钥（必填）"
    )
    
    base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        description="硅基流动API基础URL"
    )
    
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="嵌入模型名称"
    )
    
    embedding_dim: int = Field(
        default=1024,
        description="嵌入向量维度"
    )
    
    reranker_model: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        description="重排序模型名称"
    )
    
    class Config:
        env_prefix = "SILICONFLOW_"
        case_sensitive = False


class APIConfig(BaseSettings):
    """API服务配置类"""
    
    # 参数定义
    host: str = Field(
        default="0.0.0.0",
        description="API监听地址"
    )
    
    port: int = Field(
        default=8000,
        description="API监听端口"
    )
    
    workers: int = Field(
        default=3,
        description="Worker进程数量"
    )
    
    log_level: str = Field(
        default="info",
        description="日志级别"
    )
    
    semaphore_limit: int = Field(
        default=5,
        description="Graphiti并发限制"
    )
    
    class Config:
        env_prefix = "API_"
        case_sensitive = False


class AppSettings(BaseSettings):
    """应用总配置类"""
    
    # 应用级配置
    env: str = Field(
        default="development",
        description="运行环境"
    )
    
    secret_key: str = Field(
        ...,
        description="应用密钥（必填）"
    )
    
    # 子配置对象
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    deepseek: DeepSeekConfig = Field(default_factory=DeepSeekConfig)
    siliconflow: SiliconFlowConfig = Field(default_factory=SiliconFlowConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False


def load_app_config() -> AppSettings:
    """
    加载应用配置
    
    返回:
        AppSettings: 完整的应用配置对象
    
    异常:
        ValidationError: 配置验证失败
    
    流程:
        1. 从环境变量加载配置
        2. 验证必填字段
        3. 返回配置对象
    """
    return AppSettings()
