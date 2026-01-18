"""
Tests for DeepSeek Graphiti client (Week 2 implementation).
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from openai import RateLimitError, APITimeoutError, APIError
from app.services.llm.deepseek_graphiti_client import DeepSeekGraphitiClient
from graphiti_core.prompts.models import Message
from pydantic import BaseModel
import httpx


# Create mock exception classes that can be instantiated without required params
class MockRateLimitError(RateLimitError):
    """Mock RateLimitError for testing."""
    def __init__(self, message):
        # Create a mock response with all required attributes
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {}
        super().__init__(message=message, response=mock_response, body=None)


class MockAPITimeoutError(APITimeoutError):
    """Mock APITimeoutError for testing."""
    def __init__(self, message):
        # APITimeoutError only needs 'request' parameter
        mock_request = Mock(spec=httpx.Request)
        mock_request.headers = {}
        super().__init__(request=mock_request)


class MockAPIError(APIError):
    """Mock APIError for testing."""
    def __init__(self, message):
        # APIError needs 'request' parameter, not 'response'
        mock_request = Mock(spec=httpx.Request)
        mock_request.headers = {}
        super().__init__(message=message, request=mock_request, body=None)


@pytest.fixture
def deepseek_client():
    """Create a DeepSeekGraphitiClient for testing."""
    client = DeepSeekGraphitiClient(
        api_key="test_key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat"
    )
    yield client


class SampleModel(BaseModel):
    """Test Pydantic model for structured output."""
    name: str
    value: int


@pytest.mark.asyncio
async def test_deepseek_client_generate_response_success(deepseek_client):
    """Test successful LLM response generation."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # Return valid JSON
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"name": "test", "value": 42}'

        mock_to_thread.return_value = mock_response

        messages = [Message(role="user", content="Test")]
        result = await deepseek_client.generate_response(
            messages=messages,
            response_model=SampleModel,
            max_tokens=1000
        )

        # Verify parsed response
        assert "name" in result
        assert result["name"] == "test"
        assert result["value"] == 42


@pytest.mark.asyncio
async def test_deepseek_client_max_tokens_cap(deepseek_client):
    """Test that max_tokens is capped per model limits."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'

        mock_to_thread.return_value = mock_response

        messages = [Message(role="user", content="Test")]

        # Test deepseek-chat (max 4096)
        result = await deepseek_client.generate_response(
            messages=messages,
            max_tokens=10000  # Request more than limit
        )

        # Should have capped to 4096
        assert mock_to_thread.call_args[1]['max_tokens'] == 4096


@pytest.mark.asyncio
async def test_deepseek_client_rate_limit_retry(deepseek_client):
    """Test retry logic on rate limit errors."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # First call gets rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'

        # Make model_dump() return actual dict
        mock_response.model_dump.return_value = {"result": "success"}

        call_count = [0]
        async def to_thread_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise MockRateLimitError("Rate limit exceeded")
            return mock_response

        mock_to_thread.side_effect = to_thread_side_effect

        # Mock asyncio.sleep as an async function
        async def mock_sleep(seconds):
            pass

        with patch('app.services.llm.deepseek_graphiti_client.asyncio.sleep', side_effect=mock_sleep):
            messages = [Message(role="user", content="Test")]
            result = await deepseek_client.generate_response(
                messages=messages,
                max_tokens=1000
            )

            # Verify success after retry
            assert "result" in result


@pytest.mark.asyncio
async def test_deepseek_client_timeout_retry(deepseek_client):
    """Test retry logic on timeout errors."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'

        # Make model_dump() return actual dict
        mock_response.model_dump.return_value = {"result": "success"}

        call_count = [0]
        async def to_thread_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise MockAPITimeoutError("Request timeout")
            return mock_response

        mock_to_thread.side_effect = to_thread_side_effect

        # Mock asyncio.sleep as an async function
        async def mock_sleep(seconds):
            pass

        with patch('app.services.llm.deepseek_graphiti_client.asyncio.sleep', side_effect=mock_sleep):
            messages = [Message(role="user", content="Test")]
            result = await deepseek_client.generate_response(
                messages=messages,
                max_tokens=1000
            )

            # Verify success after retry
            assert "result" in result


@pytest.mark.asyncio
async def test_deepseek_client_max_retries_exceeded(deepseek_client):
    """Test that max retries is respected."""
    from app.core.exceptions import LLMError

    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # Always raise rate limit error
        async def to_thread_side_effect(*args, **kwargs):
            raise MockRateLimitError("Rate limit exceeded")

        mock_to_thread.side_effect = to_thread_side_effect

        # Mock asyncio.sleep as an async function
        async def mock_sleep(seconds):
            pass

        with patch('app.services.llm.deepseek_graphiti_client.asyncio.sleep', side_effect=mock_sleep):
            messages = [Message(role="user", content="Test")]

            with pytest.raises(LLMError) as exc_info:
                await deepseek_client.generate_response(
                    messages=messages,
                    max_tokens=1000
                )

            # Verify error message mentions retries
            assert "retries" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_deepseek_client_no_retry_on_api_error(deepseek_client):
    """Test that API errors don't trigger retries."""
    from app.core.exceptions import LLMError

    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # Raise API error
        async def to_thread_side_effect(*args, **kwargs):
            raise MockAPIError("Invalid request")

        mock_to_thread.side_effect = to_thread_side_effect

        # Mock asyncio.sleep as an async function
        async def mock_sleep(seconds):
            pass

        with patch('app.services.llm.deepseek_graphiti_client.asyncio.sleep', side_effect=mock_sleep) as mock_sleep:
            messages = [Message(role="user", content="Test")]

            with pytest.raises(LLMError):
                await deepseek_client.generate_response(
                    messages=messages,
                    max_tokens=1000
                )

            # Verify sleep was not called (no retry)
            mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_deepseek_client_json_parsing_error(deepseek_client):
    """Test JSON parsing error handling."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # Return invalid JSON
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = 'not valid json'

        mock_to_thread.return_value = mock_response

        messages = [Message(role="user", content="Test")]

        with pytest.raises(ValueError):
            await deepseek_client.generate_response(
                messages=messages,
                response_model=SampleModel,
                max_tokens=1000
            )


@pytest.mark.asyncio
async def test_deepseek_client_structured_response_parsing(deepseek_client):
    """Test Pydantic model validation."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # Return valid JSON with correct structure
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"name": "Alice", "value": 100}'

        mock_to_thread.return_value = mock_response

        messages = [Message(role="user", content="Test")]
        result = await deepseek_client.generate_response(
            messages=messages,
            response_model=SampleModel,
            max_tokens=1000
        )

        # Verify model was parsed correctly
        assert result["name"] == "Alice"
        assert result["value"] == 100


@pytest.mark.asyncio
async def test_deepseek_client_markdown_code_blocks(deepseek_client):
    """Test removal of markdown code blocks from JSON response."""
    with patch('app.services.llm.deepseek_graphiti_client.asyncio.to_thread') as mock_to_thread:
        # Return JSON wrapped in markdown code blocks
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '```json\n{"data": "test"}\n```'

        mock_to_thread.return_value = mock_response

        messages = [Message(role="user", content="Test")]

        class SimpleModel(BaseModel):
            data: str

        result = await deepseek_client.generate_response(
            messages=messages,
            response_model=SimpleModel,
            max_tokens=1000
        )

        # Verify code blocks were removed
        assert "data" in result
        assert result["data"] == "test"


@pytest.mark.asyncio
async def test_deepseek_client_clean_input(deepseek_client):
    """Test input cleaning functionality."""
    test_input = "  test content  "
    cleaned = deepseek_client._clean_input(test_input)
    assert cleaned == "test content"
