"""
Configuration management using Pydantic Settings.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with type-safe environment variable loading."""

    # API Configuration
    app_name: str = "DeepSeek V3.2 JSON Schema API"
    app_version: str = "1.0.0"
    debug: bool = False

    # DeepSeek Configuration
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com/beta"  # Beta endpoint for Strict mode
    deepseek_timeout: int = 30
    deepseek_max_retries: int = 3

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Security Configuration
    allowed_origins: List[str] = ["*"]
    api_key_header: str = "X-API-Key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
