"""
Chat completion endpoints with memory integration.
"""
from fastapi import APIRouter, HTTPException, status

from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/completions")
async def chat_completion():
    """
    Chat completion with memory retrieval.

    This endpoint will:
    - Accept chat messages
    - Search relevant memories from Graphiti
    - Build context with memory injection
    - Call DeepSeek API with enriched context
    - Return assistant response

    Returns:
        Chat completion response with memory context

    TODO: Implement in Week 7 (Context Services)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Chat completion will be implemented in Week 7"
    )
