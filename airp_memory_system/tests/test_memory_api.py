"""
Tests for Memory API endpoints (Week 2 implementation).

These are integration tests that test against the real Graphiti system.

Note: These tests use AsyncClient to avoid asyncio event loop conflicts
that occur with the synchronous TestClient when using Graphiti's async operations.
Each test resets the Graphiti client singleton to avoid event loop conflicts.
"""
import pytest
import httpx
from app.main import app
from app.services.memory.graphiti_client import _graphiti_client


@pytest.fixture
async def async_client():
    """Create an async test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
async def reset_graphiti_client():
    """
    Reset Graphiti client singleton before each test.

    This prevents asyncio event loop conflicts between tests.
    """
    global _graphiti_client
    # Close existing client if it exists
    if _graphiti_client is not None:
        try:
            await _graphiti_client.close()
        except Exception:
            pass  # Ignore cleanup errors
        _graphiti_client = None

    yield

    # Clean up after test
    if _graphiti_client is not None:
        try:
            await _graphiti_client.close()
        except Exception:
            pass  # Ignore cleanup errors
        _graphiti_client = None


@pytest.mark.asyncio
async def test_add_episode_success(async_client):
    """Test successful episode creation."""
    # Test episode creation (calls real APIs)
    response = await async_client.post(
        "/api/v1/memory/episodes",
        json={
            "name": "Test Episode",
            "episode_body": "Alice works at TechCorp in San Francisco.",
            "source": "text"
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "uuid" in data
    assert "name" in data
    assert data["name"] == "Test Episode"
    assert data["entities_count"] >= 0


@pytest.mark.asyncio
async def test_add_episode_validation_error_missing_fields(async_client):
    """Test validation error for missing required fields."""
    response = await async_client.post(
        "/api/v1/memory/episodes",
        json={
            "name": "Test"
            # Missing episode_body and source
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_episode_with_reference_time(async_client):
    """Test episode creation with custom reference time."""
    custom_time = "2024-01-01T12:00:00Z"
    response = await async_client.post(
        "/api/v1/memory/episodes",
        json={
            "name": "Test Episode",
            "episode_body": "Test content",
            "source": "text",
            "reference_time": custom_time
        }
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_episode_with_metadata(async_client):
    """Test episode creation with metadata."""
    response = await async_client.post(
        "/api/v1/memory/episodes",
        json={
            "name": "Test Episode",
            "episode_body": "Test content",
            "source": "text",
            "metadata": {"custom_field": "custom_value"}
        }
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_episode_with_group_id(async_client):
    """Test adding episode with group_id."""
    # Test with group_id
    response = await async_client.post(
        "/api/v1/memory/episodes",
        json={
            "name": "Test Episode",
            "episode_body": "Test content",
            "source": "text",
            "group_id": "test_group"
        }
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_search_success(async_client):
    """Test successful search query."""
    # First add an episode
    await async_client.post(
        "/api/v1/memory/episodes",
        json={
            "name": "Search Test Episode",
            "episode_body": "Bob is a software engineer at StartupXYZ.",
            "source": "text"
        }
    )

    # Then search
    response = await async_client.post(
        "/api/v1/memory/search",
        json={
            "query": "Bob",
            "num_results": 10
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "Bob"


@pytest.mark.asyncio
async def test_search_with_filters(async_client):
    """Test search with filters."""
    filters = {
        "group_ids": ["test_group"],
        "center_node_uuid": "node-1"
    }

    response = await async_client.post(
        "/api/v1/memory/search",
        json={
            "query": "test",
            "num_results": 5,
            "filters": filters
        }
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_with_num_results(async_client):
    """Test search with custom num_results."""
    response = await async_client.post(
        "/api/v1/memory/search",
        json={
            "query": "test",
            "num_results": 20
        }
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_validation_error_missing_query(async_client):
    """Test validation error for missing query."""
    response = await async_client.post(
        "/api/v1/memory/search",
        json={
            "num_results": 10
            # Missing query
        }
    )

    assert response.status_code == 422
