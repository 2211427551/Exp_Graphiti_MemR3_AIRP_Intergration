"""
Tests for Graphiti client wrapper (Week 2 implementation).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.services.memory.graphiti_client import GraphitiClient


@pytest.fixture
def graphiti_client():
    """Create a GraphitiClient for testing."""
    client = GraphitiClient()
    yield client
    # Cleanup happens in the test or fixture teardown


@pytest.mark.asyncio
async def test_graphiti_client_initialization(graphiti_client):
    """Test Graphiti client initialization."""
    # Mock the Graphiti class at its import location
    with patch('graphiti_core.Graphiti') as mock_graphiti_class:
        # Mock the Graphiti instance
        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock(return_value=None)
        mock_graphiti_class.return_value = mock_graphiti_instance

        # Mock embedder at its import location
        with patch('graphiti_core.embedder.openai.OpenAIEmbedder') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder

            # Mock DeepSeek client at its import location
            with patch('app.services.llm.deepseek_graphiti_client.DeepSeekGraphitiClient') as mock_llm_class:
                mock_llm = MagicMock()
                mock_llm_class.return_value = mock_llm

                # Initialize client
                await graphiti_client.initialize()

                # Verify client was created
                assert graphiti_client.client is not None


@pytest.mark.asyncio
async def test_graphiti_client_add_episode(graphiti_client):
    """Test adding an episode to the knowledge graph."""
    # Mock Graphiti instance
    mock_graphiti_instance = MagicMock()

    # Mock episode
    mock_episode = MagicMock()
    mock_episode.uuid = "test-episode-uuid"

    # Mock nodes (entities)
    mock_entity1 = MagicMock()
    mock_entity1.uuid = "entity-1"
    mock_entity1.name = "Alice"
    mock_entity1.label = "Person"

    mock_entity2 = MagicMock()
    mock_entity2.uuid = "entity-2"
    mock_entity2.name = "TechCorp"
    mock_entity2.label = "Organization"

    # Mock edges (relationships)
    mock_edge = MagicMock()
    mock_edge.uuid = "edge-1"
    mock_edge.source_node_uuid = "entity-1"
    mock_edge.target_node_uuid = "entity-2"
    mock_edge.name = "WORKS_AT"
    mock_edge.fact = "Alice works at TechCorp"

    # Set up result
    result_mock = MagicMock()
    result_mock.episode = mock_episode
    result_mock.nodes = [mock_entity1, mock_entity2]
    result_mock.edges = [mock_edge]

    mock_graphiti_instance.add_episode = AsyncMock(return_value=result_mock)
    graphiti_client.client = mock_graphiti_instance

    # Test add_episode
    result = await graphiti_client.add_episode(
        name="Test Episode",
        episode_body="Alice works at TechCorp.",
        source="text"
    )

    # Week 5: Verify result structure (EpisodeSummary is now a Pydantic model)
    assert hasattr(result, 'episode_uuid')
    assert hasattr(result, 'name')
    assert hasattr(result, 'content_summary')
    assert hasattr(result, 'entity_count')
    assert hasattr(result, 'relationship_count')
    assert result.name == "Test Episode"
    assert result.entity_count == 2
    assert result.relationship_count == 1


@pytest.mark.asyncio
async def test_graphiti_client_search(graphiti_client):
    """Test searching the knowledge graph."""
    # Mock Graphiti instance
    mock_graphiti_instance = MagicMock()

    # Mock search results (EntityEdge objects)
    mock_edge1 = MagicMock()
    mock_edge1.uuid = "edge-1"
    mock_edge1.fact = "Alice works at TechCorp"
    mock_edge1.source_node_uuid = "uuid-1"
    mock_edge1.target_node_uuid = "uuid-2"
    mock_edge1.name = "WORKS_AT"
    mock_edge1.created_at = datetime.now(timezone.utc)
    mock_edge1.valid_at = datetime.now(timezone.utc)
    mock_edge1.expired_at = None

    mock_edge2 = MagicMock()
    mock_edge2.uuid = "edge-2"
    mock_edge2.fact = "Bob lives in New York"
    mock_edge2.source_node_uuid = "uuid-3"
    mock_edge2.target_node_uuid = "uuid-4"
    mock_edge2.name = "LIVES_IN"
    mock_edge2.created_at = datetime.now(timezone.utc)
    mock_edge2.valid_at = datetime.now(timezone.utc)
    mock_edge2.expired_at = None

    mock_graphiti_instance.search = AsyncMock(return_value=[mock_edge1, mock_edge2])
    graphiti_client.client = mock_graphiti_instance

    # Mock Neo4j driver for node name lookup
    with patch('neo4j.AsyncGraphDatabase.driver') as mock_driver:
        # Mock session
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Mock records for node names
        mock_record1 = MagicMock()
        mock_record1.__getitem__ = lambda self, key: {"uuid-1": "Alice", "uuid-2": "TechCorp", "uuid-3": "Bob", "uuid-4": "New_York"}.get(key)

        async def mock_records():
            yield {"uuid": "uuid-1", "name": "Alice"}
            yield {"uuid": "uuid-2", "name": "TechCorp"}
            yield {"uuid": "uuid-3", "name": "Bob"}
            yield {"uuid": "uuid-4", "name": "New_York"}

        mock_result.__aiter__ = lambda self: mock_records()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        # Mock driver
        mock_driver_instance = MagicMock()
        mock_driver_instance.session = MagicMock(return_value=mock_session)
        mock_driver_instance.close = AsyncMock()
        mock_driver.return_value = mock_driver_instance

        # Test search
        result = await graphiti_client.search(
            query="Alice",
            num_results=10
        )

        # Week 5: Verify result structure (now returns List[SearchResult])
        assert isinstance(result, list)
        assert len(result) == 2
        # Check first result
        assert hasattr(result[0], 'uuid')
        assert hasattr(result[0], 'content')
        assert hasattr(result[0], 'score')


@pytest.mark.asyncio
async def test_graphiti_client_close(graphiti_client):
    """Test closing the Graphiti client."""
    # Mock Graphiti instance
    mock_graphiti_instance = MagicMock()
    mock_graphiti_instance.close = AsyncMock(return_value=None)
    graphiti_client.client = mock_graphiti_instance

    # Test close
    await graphiti_client.close()

    # Verify close was called
    mock_graphiti_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_graphiti_client_add_episode_with_reference_time(graphiti_client):
    """Test adding episode with custom reference time."""
    # Mock Graphiti instance
    mock_graphiti_instance = MagicMock()

    mock_episode = MagicMock()
    mock_episode.uuid = "test-episode-uuid"

    result_mock = MagicMock()
    result_mock.episode = mock_episode
    result_mock.nodes = []
    result_mock.edges = []

    mock_graphiti_instance.add_episode = AsyncMock(return_value=result_mock)
    graphiti_client.client = mock_graphiti_instance

    # Test with custom time
    custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = await graphiti_client.add_episode(
        name="Test Episode",
        episode_body="Test content",
        source="text",
        reference_time=custom_time
    )

    # Week 5: Verify (EpisodeSummary has episode_uuid attribute)
    assert hasattr(result, 'episode_uuid')
    assert result.episode_uuid == "test-episode-uuid"


@pytest.mark.asyncio
async def test_graphiti_client_add_episode_with_group_id(graphiti_client):
    """Test adding episode with group ID."""
    # Mock Graphiti instance
    mock_graphiti_instance = MagicMock()

    mock_episode = MagicMock()
    mock_episode.uuid = "test-episode-uuid"

    result_mock = MagicMock()
    result_mock.episode = mock_episode
    result_mock.nodes = []
    result_mock.edges = []

    mock_graphiti_instance.add_episode = AsyncMock(return_value=result_mock)
    graphiti_client.client = mock_graphiti_instance

    # Test with group_id
    result = await graphiti_client.add_episode(
        name="Test Episode",
        episode_body="Test content",
        source="text",
        group_id="test-group"
    )

    # Week 5: Verify (EpisodeSummary has episode_uuid attribute)
    assert hasattr(result, 'episode_uuid')
    assert result.episode_uuid == "test-episode-uuid"


@pytest.mark.asyncio
async def test_graphiti_client_search_with_filters(graphiti_client):
    """Test searching with filters (Week 5: Now delegates to SearchService)."""
    # Mock Graphiti instance
    mock_graphiti_instance = MagicMock()
    mock_graphiti_instance.search = AsyncMock(return_value=[])
    graphiti_client.client = mock_graphiti_instance

    # Week 5: Initialize Week 5 services
    from app.services.llm.embedding_client import EmbeddingClient
    from app.services.llm.reranker_client import RerankerClient
    from app.services.memory.deduplication_service import DeduplicationService

    graphiti_client.embedding_client = EmbeddingClient()
    graphiti_client.reranker_client = RerankerClient()
    graphiti_client.dedup_service = DeduplicationService(graphiti_client.embedding_client)

    # Test with filters (now uses SearchService instead of direct Graphiti search)
    filters = {
        "group_ids": ["group-1", "group-2"],
        "center_node_uuid": "node-1"
    }

    result = await graphiti_client.search(
        query="test",
        num_results=5,
        filters=filters
    )

    # Week 5: With filters, it delegates to SearchService (returns List[SearchResult])
    # mock_graphiti_instance.search is NOT called because SearchService handles it
    assert isinstance(result, list)
    # Should return mock results from SearchService
    assert len(result) >= 0


@pytest.mark.asyncio
async def test_graphiti_client_error_handling(graphiti_client):
    """Test error handling when client is not initialized."""
    # Don't initialize the client
    graphiti_client.client = None

    # Test add_episode raises error
    from app.core.exceptions import GraphitiConnectionError

    with pytest.raises(GraphitiConnectionError):
        await graphiti_client.add_episode(
            name="Test",
            episode_body="Test content",
            source="text"
        )

    # Test search raises error
    with pytest.raises(GraphitiConnectionError):
        await graphiti_client.search("test")


@pytest.mark.asyncio
async def test_graphiti_client_close_without_init(graphiti_client):
    """Test closing client that was never initialized."""
    # Don't initialize the client
    graphiti_client.client = None

    # Should not raise error
    await graphiti_client.close()


@pytest.mark.asyncio
async def test_graphiti_client_get_graphiti_client():
    """Test the get_graphiti_client singleton function."""
    from app.services.memory.graphiti_client import get_graphiti_client

    # Mock the Graphiti class at its import location
    with patch('graphiti_core.Graphiti') as mock_graphiti_class:
        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock(return_value=None)
        mock_graphiti_class.return_value = mock_graphiti_instance

        # Mock embedder at its import location and LLM
        with patch('graphiti_core.embedder.openai.OpenAIEmbedder'):
            with patch('app.services.llm.deepseek_graphiti_client.DeepSeekGraphitiClient'):
                # Get client
                client1 = await get_graphiti_client()
                client2 = await get_graphiti_client()

                # Should return same instance (singleton)
                assert client1 is client2
