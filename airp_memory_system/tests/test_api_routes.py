"""
Tests for API routes.
"""
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "AIRP Memory System"


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    # Health status can be "healthy" or "degraded" depending on service availability
    assert data["status"] in ["healthy", "degraded"]
    assert data["app_name"] == "AIRP Memory System"
    assert "components" in data
    assert data["components"]["api"] == "healthy"


def test_liveness_probe(client: TestClient):
    """Test liveness probe endpoint."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_readiness_probe(client: TestClient):
    """Test readiness probe endpoint."""
    response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_memory_episodes_validation_error(client: TestClient):
    """Test that episodes endpoint validates input data (Week 2 implemented)."""
    # Send empty data - should return 422 validation error
    response = client.post("/api/v1/memory/episodes", json={})

    # Week 2: Endpoint is now implemented, returns validation error for missing data
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_memory_search_validation_error(client: TestClient):
    """Test that search endpoint validates input data (Week 2 implemented)."""
    # Send empty data - should return 422 validation error
    response = client.post("/api/v1/memory/search", json={})

    # Week 2: Endpoint is now implemented, returns validation error for missing data
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_chat_completions_not_implemented(client: TestClient):
    """Test that chat completions endpoint returns 501."""
    response = client.post("/api/v1/chat/completions", json={})

    assert response.status_code == 501
    data = response.json()
    assert "detail" in data
    assert "Week 7" in data["detail"]


def test_api_docs_accessible(client: TestClient):
    """Test that API documentation is accessible."""
    response = client.get("/docs")

    assert response.status_code == 200


def test_redoc_accessible(client: TestClient):
    """Test that ReDoc documentation is accessible."""
    response = client.get("/redoc")

    assert response.status_code == 200
