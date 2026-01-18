"""
Tests for Embedding client (Week 2 implementation).
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.services.llm.embedding_client import EmbeddingClient


@pytest.fixture
def embedding_client():
    """Create an EmbeddingClient for testing."""
    client = EmbeddingClient(
        api_key="test_key",
        base_url="https://api.siliconflow.cn/v1",
        model="BAAI/bge-m3"
    )
    yield client


@pytest.mark.asyncio
async def test_embedding_client_embed_text(embedding_client):
    """Test single text embedding."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        # Mock response
        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.embedding = [0.1] * 1024  # 1024 dimensions for bge-m3
        mock_response.data = [mock_item]

        mock_create.return_value = mock_response

        result = await asyncio.to_thread(
            embedding_client.embed_text,
            "Test text"
        )

        # Verify embedding
        assert len(result) == 1024
        assert all(isinstance(x, float) for x in result)


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_single_text(embedding_client):
    """Test batch embedding with single text."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.embedding = [0.1] * 1024
        mock_response.data = [mock_item]

        mock_create.return_value = mock_response

        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            ["Test text"]
        )

        # Verify
        assert len(result) == 1
        assert len(result[0]) == 1024


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_multiple_texts(embedding_client):
    """Test batch embedding with 3 texts."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        mock_response = MagicMock()
        mock_data = []
        for i in range(3):
            mock_item = MagicMock()
            mock_item.embedding = [i * 0.1] * 1024
            mock_data.append(mock_item)

        mock_response.data = mock_data
        mock_create.return_value = mock_response

        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            ["Text 1", "Text 2", "Text 3"]
        )

        # Verify all embeddings returned
        assert len(result) == 3
        assert all(len(embedding) == 1024 for embedding in result)


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_large_list(embedding_client):
    """Test batch embedding with 250 texts (more than batch size)."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        call_count = [0]

        def create_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            mock_data = []

            # Get batch size from input
            texts = args[1] if len(args) > 1 else kwargs.get('input', [])
            for i in range(len(texts)):
                mock_item = MagicMock()
                mock_item.embedding = [i * 0.01] * 1024
                mock_data.append(mock_item)

            mock_response.data = mock_data
            return mock_response

        mock_create.side_effect = create_side_effect

        # Create list of 250 texts (should require 3 batches: 100 + 100 + 50)
        texts = [f"Text {i}" for i in range(250)]

        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            texts
        )

        # Verify all texts were embedded
        assert len(result) == 250
        assert all(len(embedding) == 1024 for embedding in result)

        # Verify API was called 3 times
        assert call_count[0] == 3


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_preserves_order(embedding_client):
    """Test that batch embedding preserves order."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        def create_side_effect(*args, **kwargs):
            mock_response = MagicMock()
            texts = args[1] if len(args) > 1 else kwargs.get('input', [])
            mock_data = []

            for i, text in enumerate(texts):
                mock_item = MagicMock()
                # Use unique value per text to track order
                mock_item.embedding = [float(i)] + [0.0] * 1023
                mock_data.append(mock_item)

            mock_response.data = mock_data
            return mock_response

        mock_create.side_effect = create_side_effect

        texts = ["Apple", "Banana", "Cherry"]
        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            texts
        )

        # Verify order is preserved by checking first value
        assert result[0][0] == 0.0  # Apple
        assert result[1][0] == 1.0  # Banana
        assert result[2][0] == 2.0  # Cherry


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_empty_list(embedding_client):
    """Test batch embedding with empty list."""
    result = await asyncio.to_thread(
        embedding_client.embed_batch,
        []
    )

    # Should return empty list
    assert result == []


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_with_batch_size_100(embedding_client):
    """Test that batch size is 100."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        batch_sizes = []

        def create_side_effect(*args, **kwargs):
            texts = args[1] if len(args) > 1 else kwargs.get('input', [])
            batch_sizes.append(len(texts))

            mock_response = MagicMock()
            mock_data = [MagicMock(embedding=[0.1] * 1024) for _ in texts]
            mock_response.data = mock_data
            return mock_response

        mock_create.side_effect = create_side_effect

        # Create 250 texts
        texts = [f"Text {i}" for i in range(250)]
        await asyncio.to_thread(embedding_client.embed_batch, texts)

        # Verify batch sizes (100, 100, 50)
        assert batch_sizes == [100, 100, 50]


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_handles_unicode(embedding_client):
    """Test batch embedding with Unicode characters."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        mock_response = MagicMock()
        mock_data = [MagicMock(embedding=[0.1] * 1024) for _ in range(2)]
        mock_response.data = mock_data
        mock_create.return_value = mock_response

        texts = ["Hello 世界", "Привет мир"]
        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            texts
        )

        # Should handle Unicode without errors
        assert len(result) == 2
        assert all(len(embedding) == 1024 for embedding in result)


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_with_long_texts(embedding_client):
    """Test batch embedding with very long texts."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        mock_response = MagicMock()
        mock_data = [MagicMock(embedding=[0.1] * 1024) for _ in range(2)]
        mock_response.data = mock_data
        mock_create.return_value = mock_response

        # Create very long texts (10,000 characters each)
        long_text = "A" * 10000
        texts = [long_text, long_text]

        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            texts
        )

        # Should handle long texts
        assert len(result) == 2
        assert all(len(embedding) == 1024 for embedding in result)


@pytest.mark.asyncio
async def test_embedding_client_embed_batch_error_handling(embedding_client):
    """Test error handling in batch embedding."""
    from app.core.exceptions import EmbeddingError

    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        # Raise exception
        mock_create.side_effect = Exception("API error")

        with pytest.raises(EmbeddingError) as exc_info:
            await asyncio.to_thread(
                embedding_client.embed_batch,
                ["Test text"]
            )

        # Verify error type
        assert "embedding" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_embedding_client_performance_large_batch(embedding_client):
    """Test performance with 1000 texts."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        call_count = [0]

        def create_side_effect(*args, **kwargs):
            call_count[0] += 1
            texts = args[1] if len(args) > 1 else kwargs.get('input', [])

            mock_response = MagicMock()
            mock_data = [MagicMock(embedding=[0.1] * 1024) for _ in texts]
            mock_response.data = mock_data
            return mock_response

        mock_create.side_effect = create_side_effect

        # Create 1000 texts
        texts = [f"Text {i}" for i in range(1000)]

        result = await asyncio.to_thread(
            embedding_client.embed_batch,
            texts
        )

        # Verify all embedded
        assert len(result) == 1000

        # Verify 10 API calls (100 texts per batch)
        assert call_count[0] == 10


@pytest.mark.asyncio
async def test_embedding_client_batch_api_compatibility(embedding_client):
    """Test SiliconFlow API compatibility with batch requests."""
    with patch.object(embedding_client.client.embeddings, 'create') as mock_create:
        # Track how input is passed
        input_values = []

        def create_side_effect(*args, **kwargs):
            # Capture input argument
            if len(args) > 1:
                input_values.append(('arg', args[1]))
            elif 'input' in kwargs:
                input_values.append(('kwarg', kwargs['input']))

            mock_response = MagicMock()
            mock_data = [MagicMock(embedding=[0.1] * 1024) for _ in range(3)]
            mock_response.data = mock_data
            return mock_response

        mock_create.side_effect = create_side_effect

        texts = ["A", "B", "C"]
        await asyncio.to_thread(embedding_client.embed_batch, texts)

        # Verify input was passed as a list (batch mode)
        assert len(input_values) == 1
        input_type, input_value = input_values[0]
        assert isinstance(input_value, list)
        assert len(input_value) == 3
