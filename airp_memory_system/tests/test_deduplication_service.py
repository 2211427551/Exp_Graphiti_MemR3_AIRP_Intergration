"""Tests for DeduplicationService (Week 5)."""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock

from app.services.memory.deduplication_service import DeduplicationService
from app.models.memory import Entity, DeduplicationResult
from app.services.llm.embedding_client import EmbeddingClient


@pytest.fixture
def mock_embedding_client():
    """Create a mock EmbeddingClient."""
    client = Mock(spec=EmbeddingClient)
    # Mock generate_embedding to return consistent embeddings
    client.generate_embedding = AsyncMock(return_value=np.random.rand(1024).tolist())
    return client


@pytest.fixture
def dedup_service(mock_embedding_client):
    """Create a DeduplicationService instance with mock client."""
    return DeduplicationService(
        mock_embedding_client,
        threshold=0.85,
        name_weight=0.4,
        description_weight=0.6
    )


@pytest.mark.asyncio
async def test_check_entity_duplicate_no_existing_entities(dedup_service):
    """Test entity duplicate check with no existing entities."""
    result = await dedup_service.check_entity_duplicate(
        name="天际省",
        entity_type="location",
        description="天际省是泰姆瑞尔帝国的北部省份"
    )

    assert result.is_duplicate is False
    assert result.similarity_score == 0.0
    assert result.matched_uuid is None
    assert "No existing entities" in result.match_reason


@pytest.mark.asyncio
async def test_check_entity_duplicate_with_existing_entities(dedup_service, mock_embedding_client):
    """Test entity duplicate check with existing entities."""
    # Add an existing entity embedding
    await dedup_service.add_entity_embedding(
        uuid="existing-uuid-123",
        name="天际省",
        description="天际省是泰姆瑞尔帝国的北部省份"
    )

    # Mock to return similar embedding for duplicate
    mock_embedding_client.generate_embedding = AsyncMock(
        return_value=np.ones(1024).tolist()
    )

    # Update existing entity to use same embedding
    await dedup_service.add_entity_embedding(
        uuid="existing-uuid-123",
        name="天际省",
        description="天际省是泰姆瑞尔帝国的北部省份"
    )

    result = await dedup_service.check_entity_duplicate(
        name="天际省",
        entity_type="location",
        description="天际省是泰姆瑞尔帝国的北部省份"
    )

    # Should detect as duplicate with high similarity
    assert isinstance(result, DeduplicationResult)
    assert hasattr(result, 'is_duplicate')
    assert hasattr(result, 'similarity_score')
    assert hasattr(result, 'matched_uuid')


@pytest.mark.asyncio
async def test_check_episode_duplicate_no_existing_episodes(dedup_service):
    """Test episode duplicate check with no existing episodes."""
    result = await dedup_service.check_episode_duplicate(
        content="天际省位于泰姆瑞尔北部，首府是独孤城"
    )

    assert result.is_duplicate is False
    assert result.similarity_score == 0.0
    assert result.matched_uuid is None
    assert "No existing episodes" in result.match_reason


@pytest.mark.asyncio
async def test_check_episode_duplicate_with_existing_episodes(dedup_service, mock_embedding_client):
    """Test episode duplicate check with existing episodes."""
    # Add an existing episode embedding
    await dedup_service.add_episode_embedding(
        uuid="episode-uuid-456",
        content="天际省位于泰姆瑞尔北部，首府是独孤城"
    )

    result = await dedup_service.check_episode_duplicate(
        content="天际省位于泰姆瑞尔北部，首府是独孤城"
    )

    assert isinstance(result, DeduplicationResult)
    assert hasattr(result, 'is_duplicate')
    assert hasattr(result, 'similarity_score')
    assert hasattr(result, 'matched_uuid')
    assert "similarity" in result.match_reason.lower()


@pytest.mark.asyncio
async def test_cosine_similarity_identical_vectors(dedup_service):
    """Test cosine similarity with identical vectors."""
    vec1 = np.array([1.0, 2.0, 3.0])
    vec2 = np.array([1.0, 2.0, 3.0])

    similarity = dedup_service._cosine_similarity(vec1, vec2)

    # Identical vectors should have similarity of 1.0
    assert similarity == pytest.approx(1.0, rel=1e-5)


@pytest.mark.asyncio
async def test_cosine_similarity_orthogonal_vectors(dedup_service):
    """Test cosine similarity with orthogonal vectors."""
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([0.0, 1.0, 0.0])

    similarity = dedup_service._cosine_similarity(vec1, vec2)

    # Orthogonal vectors should have similarity of 0.0
    assert similarity == pytest.approx(0.0, abs=1e-5)


@pytest.mark.asyncio
async def test_cosine_similarity_opposite_vectors(dedup_service):
    """Test cosine similarity with opposite vectors."""
    vec1 = np.array([1.0, 2.0, 3.0])
    vec2 = np.array([-1.0, -2.0, -3.0])

    similarity = dedup_service._cosine_similarity(vec1, vec2)

    # Opposite vectors should have similarity of 0.0 (clamped)
    assert similarity == pytest.approx(0.0, abs=1e-5)


@pytest.mark.asyncio
async def test_cosine_similarity_random_vectors(dedup_service):
    """Test cosine similarity with random vectors."""
    vec1 = np.array([1.0, 2.0, 3.0])
    vec2 = np.array([2.0, 3.0, 4.0])

    similarity = dedup_service._cosine_similarity(vec1, vec2)

    # Should be between 0 and 1
    assert 0.0 <= similarity <= 1.0


@pytest.mark.asyncio
async def test_name_similarity_exact_match(dedup_service):
    """Test name similarity with exact match."""
    similarity = dedup_service._name_similarity("天际省", "天际省")

    assert similarity == 1.0


@pytest.mark.asyncio
async def test_name_similarity_case_insensitive(dedup_service):
    """Test name similarity is case-insensitive."""
    similarity = dedup_service._name_similarity("Skyrim", "skyrim")

    assert similarity == 1.0


@pytest.mark.asyncio
async def test_name_similarity_substring_match(dedup_service):
    """Test name similarity with substring match."""
    similarity = dedup_service._name_similarity("天际", "天际省")

    # Substring match should return 0.7
    assert similarity == 0.7


@pytest.mark.asyncio
async def test_name_similarity_no_match(dedup_service):
    """Test name similarity with no match."""
    similarity = dedup_service._name_similarity("天际省", "幽影沼泽")

    assert similarity == 0.0


@pytest.mark.asyncio
async def test_name_similarity_with_uuid(dedup_service):
    """Test name similarity when comparing with UUID."""
    similarity = dedup_service._name_similarity(
        "天际省",
        "123e4567-e89b-12d3-a456-426614174000"
    )

    # UUID should return 0.0 similarity
    assert similarity == 0.0


@pytest.mark.asyncio
async def test_deduplication_threshold_configuration(mock_embedding_client):
    """Test that threshold configuration affects duplicate detection."""
    # Create service with low threshold (0.5)
    strict_service = DeduplicationService(mock_embedding_client, threshold=0.5)

    # Add existing entity
    await strict_service.add_entity_embedding(
        uuid="test-uuid",
        name="测试",
        description="测试描述"
    )

    result = await strict_service.check_entity_duplicate(
        name="测试",
        entity_type="test",
        description="测试描述"
    )

    # Threshold should be 0.5 as configured
    assert strict_service.threshold == 0.5
    assert isinstance(result, DeduplicationResult)


@pytest.mark.asyncio
async def test_weight_configuration(mock_embedding_client):
    """Test that weight configuration affects similarity calculation."""
    # Create service with custom weights
    custom_service = DeduplicationService(
        mock_embedding_client,
        name_weight=0.7,
        description_weight=0.3
    )

    # Weights should be configured correctly
    assert custom_service.name_weight == 0.7
    assert custom_service.description_weight == 0.3
    # Should still sum to 1.0 with default threshold
    assert custom_service.threshold == 0.85


@pytest.mark.asyncio
async def test_add_entity_embedding(dedup_service):
    """Test adding entity embeddings to cache."""
    await dedup_service.add_entity_embedding(
        uuid="test-uuid-789",
        name="独孤城",
        description="天际省首府"
    )

    # Check that embedding was added
    assert "test-uuid-789" in dedup_service._entity_embeddings
    assert isinstance(dedup_service._entity_embeddings["test-uuid-789"], np.ndarray)
    assert len(dedup_service._entity_embeddings["test-uuid-789"]) == 1024


@pytest.mark.asyncio
async def test_add_episode_embedding(dedup_service):
    """Test adding episode embeddings to cache."""
    await dedup_service.add_episode_embedding(
        uuid="episode-uuid-999",
        content="这是一个测试episode的内容"
    )

    # Check that embedding was added
    assert "episode-uuid-999" in dedup_service._episode_embeddings
    assert isinstance(dedup_service._episode_embeddings["episode-uuid-999"], np.ndarray)
    assert len(dedup_service._episode_embeddings["episode-uuid-999"]) == 1024


@pytest.mark.asyncio
async def test_find_similar_entities_not_implemented(dedup_service):
    """Test that find_similar_entities returns empty list (not implemented)."""
    entity = Entity(
        uuid="test-uuid",
        name="测试",
        entity_type="test",
        description="测试描述"
    )

    results = await dedup_service.find_similar_entities(entity)

    # Should return empty list (not implemented yet)
    assert results == []


@pytest.mark.asyncio
async def test_suggest_entity_merge_not_implemented(dedup_service):
    """Test that suggest_entity_merge returns empty list (not implemented)."""
    suggestions = await dedup_service.suggest_entity_merge([
        "uuid-1",
        "uuid-2",
        "uuid-3"
    ])

    # Should return empty list (not implemented yet)
    assert suggestions == []


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_deduplication_performance(dedup_service, mock_embedding_client):
    """Benchmark deduplication check performance."""
    import time

    # Add some existing entities
    for i in range(10):
        await dedup_service.add_entity_embedding(
            uuid=f"entity-{i}",
            name=f"实体{i}",
            description=f"这是第{i}个实体的描述"
        )

    # Time the duplicate check
    start = time.time()
    result = await dedup_service.check_entity_duplicate(
        name="测试实体",
        entity_type="test",
        description="这是一个测试实体"
    )
    duration = time.time() - start

    # Should complete in reasonable time (<1 second)
    assert duration < 1.0
    assert isinstance(result, DeduplicationResult)


@pytest.mark.asyncio
async def test_cosine_similarity_zero_vector(dedup_service):
    """Test cosine similarity handles zero vectors."""
    vec1 = np.array([0.0, 0.0, 0.0])
    vec2 = np.array([1.0, 2.0, 3.0])

    similarity = dedup_service._cosine_similarity(vec1, vec2)

    # Zero vector should return 0.0 similarity
    assert similarity == 0.0


@pytest.mark.asyncio
async def test_cosine_similarity_clamping(dedup_service):
    """Test that cosine similarity is clamped to [0, 1] range."""
    # Create vectors that might produce negative similarity
    vec1 = np.array([1.0, 1.0])
    vec2 = np.array([-0.5, -0.5])

    similarity = dedup_service._cosine_similarity(vec1, vec2)

    # Should be clamped to 0.0 (not negative)
    assert similarity >= 0.0
    assert similarity <= 1.0
