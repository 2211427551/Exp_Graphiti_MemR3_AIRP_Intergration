"""
Chat completion endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.models.requests import ChatCompletionRequest
from app.models.responses import ChatCompletionResponse
from app.services.deepseek_client import DeepSeekClient
from app.services.schema_validator import DeepSeekSchemaValidator
from app.services.schema_transformer import DeepSeekSchemaTransformer
from app.utils.exceptions import DeepSeekValidationError, DeepSeekAPIError
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_deepseek_client():
    """Dependency to get DeepSeek client instance."""
    return DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.deepseek_timeout,
        max_retries=settings.deepseek_max_retries
    )


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create chat completion",
    description="Send messages to DeepSeek V3.2 with tool calling and strict mode support"
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    client: DeepSeekClient = Depends(get_deepseek_client)
):
    """
    Create a chat completion with optional tool calling.

    - **model**: deepseek-chat or deepseek-reasoner
    - **messages**: Conversation messages
    - **tools**: Optional tool definitions for function calling
    - **temperature**: Sampling temperature (0-2)
    - **max_tokens**: Maximum tokens to generate
    - **stream**: Whether to stream responses (not yet supported)
    """
    try:
        # Process tools if provided
        tools = None
        if request.tools:
            validator = DeepSeekSchemaValidator()
            transformer = DeepSeekSchemaTransformer()

            validated_tools = []
            for tool in request.tools:
                tool_dict = tool.model_dump()
                schema = tool_dict["function"]["parameters"]

                # First, transform schema to remove unsupported attributes
                transformed_schema = transformer.transform_for_strict_mode(schema)

                # Then, validate the transformed schema
                is_valid, errors = validator.validate_schema(transformed_schema)
                if not is_valid:
                    logger.warning(
                        "Schema validation failed after transformation",
                        extra={
                            "tool_name": tool.function.name,
                            "errors": errors
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "Invalid JSON Schema for DeepSeek Strict mode",
                            "tool": tool.function.name,
                            "validation_errors": errors
                        }
                    )

                # Use the transformed schema
                tool_dict["function"]["parameters"] = transformed_schema
                validated_tools.append(tool_dict)

            tools = validated_tools

        # Prepare messages
        messages = [msg.model_dump(exclude_none=True) for msg in request.messages]

        # Call DeepSeek API
        response = client.chat_completion(
            model=request.model,
            messages=messages,
            tools=tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        logger.info(
            "Chat completion successful",
            extra={
                "model": request.model,
                "prompt_tokens": response["usage"]["prompt_tokens"],
                "completion_tokens": response["usage"]["completion_tokens"],
                "total_tokens": response["usage"]["total_tokens"]
            }
        )

        return ChatCompletionResponse(**response)

    except HTTPException:
        raise

    except DeepSeekValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "validation_error",
                "message": str(e),
                "details": e.validation_errors
            }
        )

    except DeepSeekAPIError as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "deepseek_api_error", "message": str(e)}
        )

    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Internal server error"}
        )
