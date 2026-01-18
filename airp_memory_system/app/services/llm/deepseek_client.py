"""
DeepSeek API client for LLM operations.
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core.logger import get_logger
from app.core.config import settings
from app.core.exceptions import LLMError

logger = get_logger(__name__)


class DeepSeekClient:
    """
    DeepSeek API client wrapper.

    Based on exp_dsv3_2_json_schema_compatiable pattern.

    TODO: Full implementation in Week 2
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key (uses settings if not provided)
            base_url: API base URL (uses settings if not provided)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize OpenAI client (DeepSeek-compatible)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        logger.info(
            "DeepSeek client initialized",
            extra={
                "base_url": self.base_url,
                "timeout": timeout,
            }
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call DeepSeek Chat Completions API.

        Args:
            messages: Conversation messages
            model: Model name (uses settings default if not provided)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            API response as dictionary

        Raises:
            LLMError: If API call fails

        TODO: Implement error handling in Week 2
        """
        model = model or settings.deepseek_model

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return self._response_to_dict(response)

        except Exception as e:
            logger.error("DeepSeek API error", extra={"error": str(e)})
            raise LLMError(f"DeepSeek API error: {str(e)}", provider="deepseek", model=model)

    def _response_to_dict(self, response) -> Dict[str, Any]:
        """Convert OpenAI response object to dictionary."""
        return {
            "id": response.id,
            "object": response.object,
            "created": response.created,
            "model": response.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                    },
                    "finish_reason": choice.finish_reason
                }
                for choice in response.choices
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
