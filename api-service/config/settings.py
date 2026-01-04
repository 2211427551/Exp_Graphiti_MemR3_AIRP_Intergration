import os
from typing import Dict, Any, List, Optional
from pydantic import Field, field_validator
from pydantic.fields import PrivateAttr
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # 向后兼容：如果pydantic-settings未安装，尝试使用旧版pydantic的BaseSettings
    from pydantic import BaseSettings
    SettingsConfigDict = None

class Settings(BaseSettings):
    """应用配置"""
    
    # Pydantic V2配置
    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            env_prefix=""
        )
    else:
        # 向后兼容：Pydantic V1配置
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
    
    # 应用环境
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "your_secure_secret_key_here"
    
    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    LOG_LEVEL: str = "info"
    
    # Neo4j配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "testpassword123"
    
    # Redis配置
    REDIS_URL: str = "redis://redis:6379"
    REDIS_PASSWORD: str = "your_redis_password_here"
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # OpenAI兼容API配置（支持硅基流动等）
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""  # 留空则使用OpenAI默认，可设置为https://api.siliconflow.cn/v1
    OPENAI_MODEL: str = "gpt-4o-mini"  # LLM模型，用于graphiti_core的知识提取和推理
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # 默认embedding模型，可改为qwen3embedding
    OPENAI_EMBEDDING_DIMENSION: int = 1536  # embedding维度，Qwen3-Embedding-4B为2560，OpenAI text-embedding-3-small为1536
    
    # Graphiti配置
    GRAPHITI_CORE_ENABLED: bool = False  # 是否启用graphiti_core功能
    GRAPHITI_CACHE_TTL: int = 3600
    GRAPHITI_MAX_RETRIES: int = 3
    GRAPHITI_TIMEOUT: int = 30
    GRAPHITI_MAX_ENTITIES_PER_CHUNK: int = 50
    GRAPHITI_MIN_CONFIDENCE: float = 0.7
    
    # 输入解析配置
    PARSER_REGEX_PATTERNS: List[str] = [
        r'<([^/>]+)>',      # 开标签：<Information>、<Userpersona>
        r'</([^>]+)>',      # 闭标签：</Userpersona>、</CharacterWorldInfo>
        r'<([^>]+)/>',      # 自闭合标签：<br/>、<format/>
        r'<\||([^|]+)\|>',   # 竖线分隔：<|User|>
        r'\{\{([^}]+)\}\}', # 花括号：{{persona}}、{{scenario}}
        r'\[\[([^]]+)\]\]', # 双链：[[location:夏莱办公室]]
    ]
    
    PARSER_HEURISTIC_RULES: Dict[str, Any] = {
        "dialogue_patterns": [
            r'User:.*?Assistant:',
            r'\w+:\s*[^<\n]+',  # 角色名: 对话
        ],
        "worldbook_patterns": [
            r'地点\(.*?\)',
            r'类别\(.*?\)',
            r'概念\(.*?\)',
        ],
        "character_profile_patterns": [
            r'Character_Profile_of:',
            r'character:',
        ]
    }
    
    # 去重配置
    DEDUP_MINHASH_SIGNATURE_SIZE: int = 128
    DEDUP_LSH_BANDS: int = 20
    DEDUP_SIMILARITY_THRESHOLD_HIGH: float = 0.9
    DEDUP_SIMILARITY_THRESHOLD_MEDIUM: float = 0.7
    
    # 会话配置
    SESSION_TIMEOUT_SECONDS: int = 3600
    SESSION_MAX_ENTITIES: int = 1000
    
    # 双时序模型配置
    TEMPORAL_MODEL_VERSION: str = "v1.0"
    TEMPORAL_MIGRATION_PHASE: str = "preparation"
    
    # 时间维度配置
    TEMPORAL_DEFAULT_VALIDITY_PERIOD_DAYS: int = 365
    TEMPORAL_MAX_VALIDITY_PERIOD_DAYS: int = 3650  # 10年
    TEMPORAL_TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%fZ"
    
    # 版本控制配置
    TEMPORAL_INITIAL_VERSION: int = 1
    TEMPORAL_MAX_VERSION_HISTORY: int = 1000
    
    # 并发控制配置
    TEMPORAL_OPTIMISTIC_LOCK_RETRY_COUNT: int = 3
    TEMPORAL_OPTIMISTIC_LOCK_RETRY_DELAY_MS: int = 100
    TEMPORAL_TRANSACTION_TIMEOUT_SECONDS: int = 30
    
    # 性能优化配置
    TEMPORAL_QUERY_CACHE_TTL: int = 300  # 5分钟
    TEMPORAL_QUERY_CACHE_SIZE: int = 10000
    TEMPORAL_BATCH_SIZE: int = 1000
    
    # 数据归档配置
    TEMPORAL_ARCHIVE_OLDER_THAN_DAYS: int = 180
    TEMPORAL_ARCHIVE_BATCH_SIZE: int = 10000
    
    @field_validator('TEMPORAL_MIGRATION_PHASE')
    @classmethod
    def validate_temporal_migration_phase(cls, v):
        """验证TEMPORAL_MIGRATION_PHASE的值"""
        if v not in ["preparation", "parallel", "switch", "completed"]:
            raise ValueError(f'TEMPORAL_MIGRATION_PHASE must be one of: preparation, parallel, switch, completed. Got: {v}')
        return v

    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.APP_ENV.lower() == "production"
    
    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self.APP_ENV.lower() == "development"

# 全局配置实例
settings = Settings()
