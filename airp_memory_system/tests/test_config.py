"""
Tests for configuration management.
"""
import os
from unittest.mock import patch

import pytest


def test_settings_defaults():
    """Test that Settings has correct default values."""
    from app.core.config import settings

    assert settings.app_name == "AIRP Memory System"
    assert settings.app_version == "1.0.0"
    assert settings.port == 8001
    # Note: neo4j_uri is "bolt://neo4j:7687" in .env for Docker environment
    assert "neo4j:7687" in settings.neo4j_uri or "localhost:7687" in settings.neo4j_uri


def test_settings_validation():
    """Test that Settings validates configuration."""
    from app.core.config import Settings

    # Test invalid log level
    with pytest.raises(ValueError):
        Settings(log_level="INVALID", **_get_minimal_settings())

    # Test invalid port
    with pytest.raises(ValueError):
        Settings(port=99999, **_get_minimal_settings())


def test_neo4j_config():
    """Test Neo4j configuration helper method."""
    from app.core.config import settings

    config = settings.get_neo4j_config()

    assert "uri" in config
    assert "user" in config
    assert "password" in config
    assert "database" in config
    assert config["uri"] == settings.neo4j_uri


def test_deepseek_config():
    """Test DeepSeek configuration helper method."""
    from app.core.config import settings

    config = settings.get_deepseek_config()

    assert "api_key" in config
    assert "base_url" in config
    assert "model" in config


def test_siliconflow_config():
    """Test SiliconFlow configuration helper method."""
    from app.core.config import settings

    config = settings.get_siliconflow_config()

    assert "api_key" in config
    assert "base_url" in config
    assert "embedding_model" in config
    assert "reranker_model" in config


def test_redis_config():
    """Test Redis configuration helper method."""
    from app.core.config import settings

    config = settings.get_redis_config()

    assert "host" in config
    assert "port" in config
    assert "max_connections" in config


def _get_minimal_settings():
    """Helper to get minimal required settings for testing."""
    return {
        "deepseek_api_key": "test_key",
        "siliconflow_api_key": "test_key"
    }
