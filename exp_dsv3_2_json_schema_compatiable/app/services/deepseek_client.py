"""
DeepSeek API client with retry logic and error handling.
"""
from typing import Optional, List, Dict, Any
import httpx

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from app.utils.exceptions import (
    DeepSeekAPIError,
    DeepSeekRateLimitError,
    DeepSeekTimeoutError,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class DeepSeekClient:
    """DeepSeek API client wrapper with enhanced error handling."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/beta",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key
            base_url: API base URL (use beta endpoint for strict mode)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.api_key = api_key
        self.base_url = base_url
        self.use_strict_mode = "/beta" in base_url

        # Initialize OpenAI client (DeepSeek-compatible)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            http_client=httpx.Client(
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30
                )
            )
        )

        logger.info(
            "DeepSeek client initialized",
            extra={
                "base_url": base_url,
                "strict_mode": self.use_strict_mode,
                "timeout": timeout,
            }
        )

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Call DeepSeek Chat Completions API.

        Args:
            model: Model name (deepseek-chat or deepseek-reasoner)
            messages: Conversation messages
            tools: Optional tool definitions for function calling
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response

        Returns:
            API response as dictionary

        Raises:
            DeepSeekAPIError: API call fails
            DeepSeekRateLimitError: Rate limit exceeded
            DeepSeekTimeoutError: Request timeout
        """
        try:
            # Build request parameters
            request_params: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }

            if tools:
                request_params["tools"] = tools

            if temperature is not None:
                request_params["temperature"] = temperature

            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens

            logger.info(
                "Sending chat completion request",
                extra={
                    "model": model,
                    "num_messages": len(messages),
                    "has_tools": tools is not None,
                }
            )

            # Send request
            response = self.client.chat.completions.create(**request_params)

            # Convert to dictionary
            response_dict = self._response_to_dict(response)

            logger.info(
                "Chat completion successful",
                extra={
                    "model": model,
                    "prompt_tokens": response_dict["usage"]["prompt_tokens"],
                    "completion_tokens": response_dict["usage"]["completion_tokens"],
                    "total_tokens": response_dict["usage"]["total_tokens"],
                }
            )

            return response_dict

        except RateLimitError as e:
            logger.error("Rate limit exceeded", extra={"error": str(e)})
            raise DeepSeekRateLimitError(f"Rate limit exceeded: {str(e)}")

        except APITimeoutError as e:
            logger.error("Request timeout", extra={"error": str(e)})
            raise DeepSeekTimeoutError(f"Request timeout: {str(e)}")

        except APIError as e:
            logger.error("DeepSeek API error", extra={"error": str(e)})
            raise DeepSeekAPIError(f"DeepSeek API error: {str(e)}")

        except Exception as e:
            logger.exception("Unexpected error during API call")
            raise DeepSeekAPIError(f"Unexpected error: {str(e)}")

    def _response_to_dict(self, response) -> Dict[str, Any]:
        """Convert OpenAI response object to dictionary.

        Args:
            response: OpenAI response object

        Returns:
            Response as dictionary
        """
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
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                }
                            }
                            for tc in (choice.message.tool_calls or [])
                        ]
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
