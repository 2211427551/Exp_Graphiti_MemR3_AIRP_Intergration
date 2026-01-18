"""
Custom LLM client for Graphiti that converts structured outputs to prompt-based JSON.

This client wraps the OpenAI client and converts Pydantic response_model requests
into JSON prompts, allowing models like DeepSeek to work with Graphiti without
native structured output support.
"""
import asyncio
import json
from typing import Any, Optional, Type
from pydantic import BaseModel
from openai import OpenAI
from openai import RateLimitError, APITimeoutError, APIError

from app.core.logger import get_logger
from app.core.config import settings
from app.core.exceptions import LLMError

# Import Graphiti-specific types
from graphiti_core.prompts.models import Message
from graphiti_core.llm_client.config import ModelSize, DEFAULT_MAX_TOKENS
from graphiti_core.llm_client.client import LLMClient

logger = get_logger(__name__)

# Define DEFAULT_MODEL locally since it's not available in Graphiti 0.26.0
DEFAULT_MODEL = "deepseek-chat"

# DeepSeek model limits
# deepseek-chat: max_tokens limit is 4096
# deepseek-reasoner: max_tokens limit is 8192
DEEPSEEK_MAX_TOKENS_LIMIT = {
    "deepseek-chat": 4096,
    "deepseek-reasoner": 8192,
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # Base delay in seconds


class DeepSeekGraphitiClient(LLMClient):
    """
    Custom LLM client for Graphiti that supports DeepSeek API.

    This client converts Pydantic response_model requests into JSON prompts,
    enabling DeepSeek to work with Graphiti's entity extraction without
    requiring native structured output support.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key (uses settings if not provided)
            base_url: API base URL (uses settings if not provided)
            model: Model name (uses settings if not provided)
        """
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.model = model or settings.graphiti_llm_model

        # Initialize OpenAI client (DeepSeek-compatible)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(
            "DeepSeekGraphitiClient initialized",
            extra={
                "base_url": self.base_url,
                "model": self.model,
            }
        )

    def set_tracer(self, tracer) -> None:
        """Set OpenTelemetry tracer for this client.

        Args:
            tracer: OpenTelemetry tracer instance
        """
        self.tracer = tracer
        logger.debug("Tracer set on DeepSeekGraphitiClient")

    async def generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
        group_id: Optional[str] = None,
        prompt_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate LLM response using Graphiti's Message format.

        Args:
            messages: Graphiti Message objects
            response_model: Optional Pydantic model for structured output
            max_tokens: Maximum tokens to generate
            model_size: Model size (ignored for DeepSeek)
            group_id: Optional group ID for logging
            prompt_name: Optional prompt name for logging

        Returns:
            Dictionary with response data
        """
        try:
            # Call the abstract method that handles the actual generation
            return await self._generate_response(
                messages=messages,
                response_model=response_model,
                max_tokens=max_tokens,
                model_size=model_size,
            )

        except Exception as e:
            logger.error(
                "Failed to generate response",
                extra={
                    "error": str(e),
                    "model": self.model,
                    "group_id": group_id,
                    "prompt_name": prompt_name,
                }
            )
            raise

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        """
        Internal method to generate response using DeepSeek API.

        Args:
            messages: Graphiti Message objects
            response_model: Optional Pydantic model for structured output
            max_tokens: Maximum tokens to generate
            model_size: Model size (ignored for DeepSeek)

        Returns:
            Dictionary with response data
        """
        # Convert Graphiti Message objects to OpenAI format
        openai_messages = []
        for m in messages:
            # Clean the input content
            content = self._clean_input(m.content)
            if m.role == 'user':
                openai_messages.append({'role': 'user', 'content': content})
            elif m.role == 'system':
                openai_messages.append({'role': 'system', 'content': content})
            else:
                # Handle other message types if needed
                openai_messages.append({'role': m.role, 'content': content})

        try:
            # Prepare response format - DeepSeek doesn't support response_format parameter at all
            # We'll rely solely on system prompts for structured output
            response_format = None

            if response_model is not None:
                # Create a strict prompt that enforces the exact schema structure
                schema_name = getattr(response_model, '__name__', 'structured_response')
                json_schema = response_model.model_json_schema()

                # Create a very specific prompt that includes examples
                # Use dynamic example generation from the actual schema
                example_data = self._generate_example_from_schema(json_schema)

                prompt = f"""You must respond with valid JSON that follows this exact schema:

{json.dumps(json_schema, indent=2)}

DO NOT create your own schema or structure. You must use the schema above exactly as provided.

Example format:
{json.dumps(example_data, indent=2)}

CRITICAL REQUIREMENTS:
1. Use field names EXACTLY as shown in the schema above
2. Output ONLY the JSON, no other text (no markdown code blocks)
3. Ensure the response matches the schema structure exactly
"""

                # Add this strict prompt to the messages
                openai_messages = self._add_schema_prompt_to_messages(openai_messages, prompt)

            # Cap max_tokens based on model limits
            model = self.model or DEFAULT_MODEL
            model_max_tokens = DEEPSEEK_MAX_TOKENS_LIMIT.get(model, 4096)
            effective_max_tokens = min(max_tokens, model_max_tokens)

            logger.debug(
                "Capping max_tokens for DeepSeek API",
                extra={
                    "model": model,
                    "requested_max_tokens": max_tokens,
                    "effective_max_tokens": effective_max_tokens,
                    "model_max_tokens": model_max_tokens,
                }
            )

            # Call DeepSeek API with retry logic
            last_error = None
            for attempt in range(MAX_RETRIES):
                try:
                    logger.debug(
                        "DeepSeek API request attempt",
                        extra={
                            "model": model,
                            "attempt": attempt + 1,
                            "max_retries": MAX_RETRIES,
                        }
                    )

                    # Call DeepSeek API in a thread pool to avoid blocking the event loop
                    response = await asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=model,
                        messages=openai_messages,
                        max_tokens=effective_max_tokens,
                    )

                    logger.debug(
                        "DeepSeek API request succeeded",
                        extra={
                            "model": model,
                            "attempt": attempt + 1,
                        }
                    )

                    break  # Success, exit retry loop

                except RateLimitError as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        # Exponential backoff for rate limits
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        logger.warning(
                            "Rate limit hit, retrying with exponential backoff",
                            extra={
                                "attempt": attempt + 1,
                                "wait_time": wait_time,
                                "error": str(e),
                            }
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("Max retries reached for rate limit error")
                        raise LLMError(
                            f"Rate limit error after {MAX_RETRIES} retries",
                            provider="deepseek",
                            model=model
                        ) from e

                except APITimeoutError as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        # Exponential backoff for timeouts
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        logger.warning(
                            "Timeout error, retrying with exponential backoff",
                            extra={
                                "attempt": attempt + 1,
                                "wait_time": wait_time,
                                "error": str(e),
                            }
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("Max retries reached for timeout error")
                        raise LLMError(
                            f"Timeout error after {MAX_RETRIES} retries",
                            provider="deepseek",
                            model=model
                        ) from e

                except APIError as e:
                    # Don't retry on API errors (likely a real problem)
                    logger.error(
                        "DeepSeek API error (not retrying)",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                    raise LLMError(
                        f"DeepSeek API error: {str(e)}",
                        provider="deepseek",
                        model=model
                    ) from e

                except Exception as e:
                    # Log unexpected error and check if we should retry
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        logger.warning(
                            "Unexpected error, retrying",
                            extra={
                                "attempt": attempt + 1,
                                "wait_time": wait_time,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("Max retries reached for unexpected error")
                        raise LLMError(
                            f"Unexpected error after {MAX_RETRIES} retries: {str(e)}",
                            provider="deepseek",
                            model=model
                        ) from e

            # Handle structured response
            if response_model is not None:
                # Parse JSON response and validate against Pydantic model
                content = response.choices[0].message.content

                # Remove markdown code blocks if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                elif content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to parse JSON response",
                        extra={
                            "error": str(e),
                            "content": content[:500],
                        }
                    )
                    raise ValueError(f"Invalid JSON response: {content}") from e

                # Validate against Pydantic model
                try:
                    model_instance = response_model(**data)
                    # Return the model dump directly, not wrapped in {"parsed": ...}
                    # This matches the OpenAI client's behavior: return response_object.parsed.model_dump()
                    return model_instance.model_dump()
                except Exception as e:
                    logger.error(
                        "Failed to validate response against model",
                        extra={
                            "error": str(e),
                            "response_model": response_model.__name__,
                            "data": str(data)[:500],
                        }
                    )
                    raise

            # Return raw response as dict
            return response.model_dump()

        except Exception as e:
            logger.error(
                "Failed to generate response",
                extra={"error": str(e), "model": self.model}
            )
            raise


    def _create_schema_prompt(self, json_schema: dict, schema_name: str) -> str:
        """Create a system prompt that describes the JSON schema to the model.

        Args:
            json_schema: JSON schema from Pydantic model
            schema_name: Name of the schema (for debugging)

        Returns:
            System prompt string
        """
        # Create a strict JSON schema prompt based on the Pydantic model
        prompt = f"You must respond with valid JSON that follows this exact JSON schema:\n\n"

        # Include the full JSON schema
        prompt += json.dumps(json_schema, indent=2)
        prompt += f"\n\nRequirements:"
        prompt += "1. Output ONLY valid JSON, no other text"
        prompt += "2. Follow the schema structure exactly"
        prompt += "3. Include all required fields with correct data types"
        prompt += "4. Do not add any extra fields beyond what's in the schema"

        return prompt

    def _add_schema_prompt_to_messages(
        self,
        messages: list[dict[str, str]],
        schema_prompt: str
    ) -> list[dict[str, str]]:
        """Add schema prompt to the first system message or create a new one.

        Args:
            messages: List of message dictionaries
            schema_prompt: Schema description prompt

        Returns:
            Updated message list with schema prompt
        """
        # Check if there's already a system message
        for i, msg in enumerate(messages):
            if msg.get('role') == 'system':
                # Prepend schema prompt to existing system message
                updated_msg = {
                    'role': 'system',
                    'content': f"{schema_prompt}\n\n{msg['content']}"
                }
                messages[i] = updated_msg
                return messages

        # No system message found, add one at the beginning
        messages.insert(0, {'role': 'system', 'content': schema_prompt})
        return messages

    def _generate_example_from_schema(self, json_schema: dict) -> dict:
        """Generate example data from JSON schema.

        Args:
            json_schema: JSON schema from Pydantic model

        Returns:
            Example data matching the schema
        """
        def generate_value(schema: dict, property_name: str = "") -> Any:
            """Generate example value for a schema property."""
            if "$ref" in schema:
                # Handle references to other schemas
                return {}

            prop_type = schema.get("type")

            if prop_type == "object":
                result = {}
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                for prop_name, prop_schema in properties.items():
                    if prop_name in required or not result:
                        result[prop_name] = generate_value(prop_schema, prop_name)
                return result

            elif prop_type == "array":
                items_schema = schema.get("items", {})
                # Generate one example item
                return [generate_value(items_schema, property_name)]

            elif prop_type == "string":
                description = schema.get("description", "")
                if "name" in property_name.lower() and "entity" in property_name.lower():
                    return "Alice"
                elif "entity" in property_name.lower() and "type" in property_name.lower():
                    return "1"
                elif "uuid" in property_name.lower():
                    return "550e8400-e29b-41d4-a716-446655440000"
                elif "fact" in property_name.lower():
                    return "Alice works at TechCorp as a software engineer."
                elif "description" in property_name.lower():
                    return "A brief description"
                else:
                    return "example_string"

            elif prop_type == "integer":
                if "entity_type_id" in property_name:
                    return 1
                return 0

            elif prop_type == "number":
                return 0.0

            elif prop_type == "boolean":
                return True

            else:
                return None

        # Generate example from root schema
        return generate_value(json_schema)

    def _clean_input(self, content: str) -> str:
        """Clean input content by removing potentially problematic characters.

        Args:
            content: Input string to clean

        Returns:
            Cleaned content string
        """
        # Remove any problematic characters
        # This is a simple implementation - can be enhanced
        return content.strip()
