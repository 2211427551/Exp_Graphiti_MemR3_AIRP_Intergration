"""
Pytest configuration and fixtures for AIRP Memory System tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application.

    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
def sample_episode_input():
    """Create a sample episode input for testing.

    Returns:
        dict: Sample episode input
    """
    from datetime import datetime

    return {
        "name": "Test Episode",
        "episode_body": "Alice works as a software engineer at TechCorp.",
        "source": "text",
        "source_description": "Test data",
        "reference_time": datetime.utcnow().isoformat(),
        "group_id": "test_group",
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_search_request():
    """Create a sample search request for testing.

    Returns:
        dict: Sample search request
    """
    return {
        "query": "What do we know about Alice?",
        "num_results": 10,
        "filters": {
            "entity_types": ["Person", "Organization"]
        }
    }
