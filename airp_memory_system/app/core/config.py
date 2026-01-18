"""
Configuration management using Pydantic Settings.
Based on exp_dsv3_2_json_schema_compatiable pattern.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application configuration with type-safe environment variable loading."""

    # ============================================
    # Application Configuration
    # ============================================
    app_name: str = "AIRP Memory System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # ============================================
    # Server Configuration
    # ============================================
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1

    # ============================================
    # Neo4j Configuration
    # ============================================
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # Neo4j Connection Pool
    neo4j_max_connections: int = 50
    neo4j_max_acquisition_time: int = 60
    neo4j_max_transaction_retry_time: int = 30

    # ============================================
    # DeepSeek API Configuration
    # ============================================
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 30
    deepseek_max_retries: int = 3

    # ============================================
    # SiliconFlow API Configuration
    # ============================================
    siliconflow_api_key: str
    siliconflow_base_url: str = "https://api.siliconflow.cn"
    siliconflow_embedding_model: str = "BAAI/bge-m3"
    siliconflow_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    siliconflow_embedding_dimensions: int = 1024
    siliconflow_timeout: int = 30
    siliconflow_max_retries: int = 3

    # ============================================
    # Redis Configuration
    # ============================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_max_connections: int = 20
    redis_cache_ttl: int = 3600

    # ============================================
    # Logging Configuration
    # ============================================
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    log_file: Optional[str] = None

    # ============================================
    # Graphiti Configuration
    # ============================================
    graphiti_enable_indices: bool = True
    graphiti_search_num_results: int = 10
    graphiti_episode_batch_size: int = 10
    graphiti_llm_provider: str = "deepseek"
    graphiti_llm_model: str = "deepseek-chat"
    graphiti_llm_temperature: float = 0.1
    graphiti_embedding_provider: str = "siliconflow"
    graphiti_embedding_model: str = "BAAI/bge-m3"

    # ============================================
    # Security Configuration
    # ============================================
    allowed_origins: List[str] = Field(default=["*"])
    api_key_header: str = "X-API-Key"
    api_key: Optional[str] = None

    # ============================================
    # CORS Configuration
    # ============================================
    cors_allow_origins: List[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = Field(default=["*"])
    cors_allow_headers: List[str] = Field(default=["*"])

    # ============================================
    # Parser Configuration
    # ============================================
    parser_min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    parser_enable_caching: bool = True
    parser_max_workers: int = Field(default=4, ge=1, le=16)

    # Format Detector Configuration
    format_detector_strict_mode: bool = False
    format_detector_min_instruction_length: int = 10

    # Content Classifier Configuration
    content_classifier_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    content_classifier_min_block_size: int = 5

    # World Info Parser Configuration
    world_info_parser_compute_hashes: bool = True
    world_info_parser_max_entry_length: int = 10000

    # Hash Computation Configuration
    hash_computation_algorithm: str = Field(
        default="md5",
        description="Hash algorithm (md5, xxhash, sha256)"
    )
    hash_computation_enable_cache: bool = Field(
        default=True,
        description="Enable LRU caching for hash computation"
    )
    hash_computation_cache_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of cached hashes"
    )

    # Change Detection Configuration
    change_detection_enable_hash_verification: bool = Field(
        default=True,
        description="Verify hash integrity during change detection"
    )
    change_detection_batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Batch size for change detection"
    )

    # ============================================
    # Week 5: Memory Service Configuration
    # ============================================

    # Entity Manager Configuration
    entity_manager_enable_cache: bool = Field(
        default=True,
        description="Enable entity caching for faster lookups"
    )
    entity_manager_cache_ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Entity cache TTL in seconds"
    )

    # Search Service Configuration
    search_default_strategy: str = Field(
        default="hybrid",
        description="Default search strategy (vector, keyword, graph, hybrid)"
    )
    search_hybrid_vector_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for vector search in hybrid mode"
    )
    search_hybrid_keyword_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for keyword search in hybrid mode"
    )
    search_hybrid_graph_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Weight for graph traversal in hybrid mode"
    )
    search_max_results: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of search results to return"
    )

    # Deduplication Configuration
    deduplication_enabled: bool = Field(
        default=True,
        description="Enable deduplication for episodes and entities"
    )
    deduplication_similarity_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=0.99,
        description="Similarity threshold for duplicate detection"
    )
    deduplication_entity_name_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for entity name similarity"
    )
    deduplication_entity_description_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for entity description similarity"
    )

    # Graphiti Integration Configuration
    graphiti_enable_entity_extraction: bool = Field(
        default=True,
        description="Enable automatic entity extraction from episodes"
    )
    graphiti_enable_relationship_extraction: bool = Field(
        default=True,
        description="Enable automatic relationship extraction from episodes"
    )
    graphiti_max_entities_per_episode: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of entities to extract per episode"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Invalid port: {v}. Must be between 1 and 65535")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_neo4j_config(self) -> dict:
        """Get Neo4j configuration as dictionary."""
        return {
            "uri": self.neo4j_uri,
            "user": self.neo4j_user,
            "password": self.neo4j_password,
            "database": self.neo4j_database,
            "max_connection_pool_size": self.neo4j_max_connections,
            "max_acquisition_time": self.neo4j_max_acquisition_time,
            "max_transaction_retry_time": self.neo4j_max_transaction_retry_time,
        }

    def get_deepseek_config(self) -> dict:
        """Get DeepSeek configuration as dictionary."""
        return {
            "api_key": self.deepseek_api_key,
            "base_url": self.deepseek_base_url,
            "model": self.deepseek_model,
            "timeout": self.deepseek_timeout,
            "max_retries": self.deepseek_max_retries,
        }

    def get_siliconflow_config(self) -> dict:
        """Get SiliconFlow configuration as dictionary."""
        return {
            "api_key": self.siliconflow_api_key,
            "base_url": self.siliconflow_base_url,
            "embedding_model": self.siliconflow_embedding_model,
            "reranker_model": self.siliconflow_reranker_model,
            "embedding_dimensions": self.siliconflow_embedding_dimensions,
            "timeout": self.siliconflow_timeout,
            "max_retries": self.siliconflow_max_retries,
        }

    def get_redis_config(self) -> dict:
        """Get Redis configuration as dictionary."""
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "password": self.redis_password,
            "db": self.redis_db,
            "max_connections": self.redis_max_connections,
            "decode_responses": True,
        }


# Global settings instance
settings = Settings()
