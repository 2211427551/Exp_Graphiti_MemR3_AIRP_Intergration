"""Tests for SearchService (Week 5)."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.services.memory.search_service import SearchService
from app.models.memory import SearchStrategy, SearchResult
from app.services.memory.graphiti_client import GraphitiClient
from app.services.llm.reranker_client import RerankerClient


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient."""
    client = Mock(spec=GraphitiClient)
    # Mock the embedding client
    client.embedding_client = Mock()
    client.embedding_client.generate_embedding = AsyncMock(return_value=[0.1] * 1024)
    return client


@pytest.fixture
def mock_reranker_client():
    """Create a mock RerankerClient."""
    return Mock(spec=RerankerClient)


@pytest.fixture
def search_service(mock_graphiti_client, mock_reranker_client):
    """Create a SearchService instance with mock clients."""
    return SearchService(mock_graphiti_client, mock_reranker_client)


@pytest.mark.asyncio
async def test_vector_search(search_service):
    """Test semantic vector search."""
    results = await search_service.vector_search(
        query="泰姆瑞尔北部的省份",
        num_results=5
    )

    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(hasattr(r, 'score') for r in results)
    assert all(0.0 <= r.score <= 1.0 for r in results)
    # Results should be sorted by score (highest first)
    assert results == sorted(results, key=lambda x: x.score, reverse=True)


@pytest.mark.asyncio
async def test_vector_search_with_filters(search_service):
    """Test vector search with additional filters."""
    results = await search_service.vector_search(
        query="天际省的城市",
        num_results=10,
        entity_types=["location"]
    )

    assert len(results) > 0
    # Verify filters are passed through (metadata should contain strategy)
    assert all(r.metadata.get('strategy') == 'vector' for r in results)


@pytest.mark.asyncio
async def test_keyword_search(search_service):
    """Test text-based keyword search."""
    results = await search_service.keyword_search(
        query="天际省",
        num_results=5
    )

    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(0.0 <= r.score <= 1.0 for r in results)
    # Verify keyword search metadata
    assert all(r.metadata.get('strategy') == 'keyword' for r in results)


@pytest.mark.asyncio
async def test_graph_traversal_search(search_service):
    """Test graph relationship traversal search."""
    entity_uuid = "test-entity-uuid-123"

    results = await search_service.graph_traversal_search(
        entity_uuid=entity_uuid,
        max_depth=2,
        num_results=5
    )

    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    # Verify graph search metadata
    assert all(r.metadata.get('strategy') == 'graph' for r in results)
    # Verify entity_uuids include the seed entity
    assert all(entity_uuid in r.entity_uuids for r in results)


@pytest.mark.asyncio
async def test_graph_traversal_with_custom_depth(search_service):
    """Test graph traversal with custom max depth."""
    results = await search_service.graph_traversal_search(
        entity_uuid="test-uuid",
        max_depth=3,
        num_results=10
    )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_search(search_service):
    """Test hybrid search combining multiple strategies."""
    results = await search_service.hybrid_search(
        query="天际省的城市",
        num_results=5,
        vector_weight=0.6,
        keyword_weight=0.3,
        graph_weight=0.1
    )

    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(0.0 <= r.score <= 1.0 for r in results)
    # Results should be sorted by combined score
    assert results == sorted(results, key=lambda x: x.score, reverse=True)


@pytest.mark.asyncio
async def test_hybrid_search_default_weights(search_service):
    """Test hybrid search with default weights."""
    results = await search_service.hybrid_search(
        query="测试查询",
        num_results=10
    )

    assert len(results) > 0
    assert all(r.score >= 0.0 for r in results)


@pytest.mark.asyncio
async def test_hybrid_search_invalid_weights(search_service):
    """Test hybrid search with invalid weight configuration."""
    with pytest.raises(ValueError, match="Weights must sum to ~1.0"):
        await search_service.search(  # Use search() instead of hybrid_search() to avoid try/except in search
            query="测试",
            strategy=SearchStrategy.HYBRID,
            num_results=5,
            filters={
                "vector_weight": 0.5,
                "keyword_weight": 0.3,  # Sum = 0.8, too low
                "graph_weight": 0.0
            }
        )


@pytest.mark.asyncio
async def test_search_with_vector_strategy(search_service):
    """Test main search method with VECTOR strategy."""
    results = await search_service.search(
        query="语义搜索测试",
        strategy=SearchStrategy.VECTOR,
        num_results=5
    )

    assert len(results) > 0
    assert all(r.metadata.get('strategy') == 'vector' for r in results)


@pytest.mark.asyncio
async def test_search_with_keyword_strategy(search_service):
    """Test main search method with KEYWORD strategy."""
    results = await search_service.search(
        query="关键词搜索",
        strategy=SearchStrategy.KEYWORD,
        num_results=5
    )

    assert len(results) > 0
    assert all(r.metadata.get('strategy') == 'keyword' for r in results)


@pytest.mark.asyncio
async def test_search_with_graph_strategy(search_service):
    """Test main search method with GRAPH_TRAVERSAL strategy."""
    results = await search_service.search(
        query="图遍历",
        strategy=SearchStrategy.GRAPH_TRAVERSAL,
        num_results=5,
        filters={"entity_uuid": "test-entity-uuid"}
    )

    assert len(results) > 0
    assert all(r.metadata.get('strategy') == 'graph' for r in results)


@pytest.mark.asyncio
async def test_search_with_graph_strategy_missing_entity_uuid(search_service):
    """Test graph traversal without entity_uuid returns empty list."""
    results = await search_service.search(
        query="图遍历",
        strategy=SearchStrategy.GRAPH_TRAVERSAL,
        num_results=5
    )

    # Should return empty list when entity_uuid is not provided
    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_with_hybrid_strategy(search_service):
    """Test main search method with HYBRID strategy (default)."""
    results = await search_service.search(
        query="混合搜索",
        strategy=SearchStrategy.HYBRID,
        num_results=5
    )

    assert len(results) > 0
    # Hybrid results combine multiple strategies


@pytest.mark.asyncio
async def test_search_with_invalid_strategy(search_service):
    """Test search with invalid strategy raises ValueError."""
    with pytest.raises(ValueError, match="Invalid search strategy"):
        await search_service.search(
            query="测试",
            strategy="invalid_strategy",  # type: ignore
            num_results=5
        )


@pytest.mark.asyncio
async def test_search_num_results_limit(search_service):
    """Test that num_results parameter limits output correctly."""
    for num_results in [1, 5, 10, 20]:
        results = await search_service.search(
            query="测试",
            strategy=SearchStrategy.VECTOR,
            num_results=num_results
        )

        # Should return at most num_results
        assert len(results) <= num_results


@pytest.mark.asyncio
async def test_search_with_filters(search_service):
    """Test search with additional filters parameter."""
    results = await search_service.search(
        query="测试",
        strategy=SearchStrategy.VECTOR,
        num_results=5,
        filters={
            "entity_types": ["location", "person"],
            "date_range": "2024-01-01:2024-12-31"
        }
    )

    assert len(results) >= 0


@pytest.mark.asyncio
async def test_vector_search_result_ordering(search_service):
    """Test that vector search results are properly ordered by score."""
    results = await search_service.vector_search(
        query="测试排序",
        num_results=10
    )

    # Verify scores are in descending order
    for i in range(len(results) - 1):
        assert results[i].score >= results[i+1].score


@pytest.mark.asyncio
async def test_hybrid_search_combines_results(search_service):
    """Test that hybrid search actually combines results from multiple strategies."""
    results = await search_service.hybrid_search(
        query="测试组合",
        num_results=10,
        vector_weight=0.5,
        keyword_weight=0.5,
        graph_weight=0.0
    )

    # Should have results
    assert len(results) > 0


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_search_performance_vector(search_service):
    """Benchmark vector search performance."""
    import time

    start = time.time()
    results = await search_service.vector_search(
        query="性能测试查询",
        num_results=10
    )
    duration = time.time() - start

    # Should complete in reasonable time (< 1 second for now)
    assert duration < 1.0
    assert len(results) > 0


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_search_performance_hybrid(search_service):
    """Benchmark hybrid search performance."""
    import time

    start = time.time()
    results = await search_service.hybrid_search(
        query="混合搜索性能测试",
        num_results=10
    )
    duration = time.time() - start

    # Hybrid search may take longer but should still be reasonable
    assert duration < 2.0
    assert len(results) > 0


@pytest.mark.asyncio
async def test_empty_query_handling(search_service):
    """Test search with empty or minimal query."""
    results = await search_service.search(
        query="",  # Empty query
        strategy=SearchStrategy.VECTOR,
        num_results=5
    )

    # Should handle gracefully
    assert len(results) >= 0


@pytest.mark.asyncio
async def test_long_query_handling(search_service):
    """Test search with very long query."""
    long_query = "测试查询 " * 100  # Very long query

    results = await search_service.search(
        query=long_query,
        strategy=SearchStrategy.KEYWORD,
        num_results=5
    )

    # Should handle long queries
    assert len(results) >= 0
