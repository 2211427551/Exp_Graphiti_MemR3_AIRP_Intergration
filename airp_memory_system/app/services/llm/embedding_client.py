"""
SiliconFlow Embedding API client.
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core.logger import get_logger
from app.core.config import settings
from app.core.exceptions import EmbeddingError

logger = get_logger(__name__)


class EmbeddingClient:
    """
    SiliconFlow Embedding client wrapper.

    Provides text vectorization using bge-m3 model (1024 dimensions).

    TODO: Full implementation in Week 2
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize Embedding client.

        Args:
            api_key: SiliconFlow API key
            base_url: API base URL
            model: Embedding model name
        """
        self.api_key = api_key or settings.siliconflow_api_key
        self.base_url = base_url or settings.siliconflow_base_url
        self.model = model or settings.siliconflow_embedding_model

        # Initialize OpenAI client (SiliconFlow-compatible)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(
            "Embedding client initialized",
            extra={
                "base_url": self.base_url,
                "model": self.model,
            }
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions for bge-m3)

        Raises:
            EmbeddingError: If embedding generation fails

        TODO: Implement in Week 2
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error("Embedding generation error", extra={"error": str(e)})
            raise EmbeddingError(f"Embedding error: {str(e)}", provider="siliconflow", model=self.model)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batch optimization.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails

        Note:
            SiliconFlow API supports batching. We process in chunks of 100
            for optimal performance while avoiding rate limits.
        """
        if not texts:
            return []

        try:
            # SiliconFlow supports batch requests
            # Process in chunks of 100 to avoid rate limits and API limits
            batch_size = 100
            all_embeddings = []

            logger.info(
                "Starting batch embedding generation",
                extra={
                    "total_texts": len(texts),
                    "batch_size": batch_size,
                }
            )

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                logger.debug(
                    "Processing embedding batch",
                    extra={
                        "batch_index": i // batch_size + 1,
                        "batch_size": len(batch),
                        "total_texts": len(texts),
                    }
                )

                # Use the API's batch endpoint - pass list directly
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch  # Pass list for batch processing
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.debug(
                    "Embedding batch completed",
                    extra={
                        "batch_index": i // batch_size + 1,
                        "embedding_dimensions": len(batch_embeddings[0]) if batch_embeddings else 0,
                    }
                )

            logger.info(
                "Batch embedding generation completed",
                extra={
                    "total_texts": len(texts),
                    "embedding_dimensions": len(all_embeddings[0]) if all_embeddings else 0,
                }
            )

            return all_embeddings

        except Exception as e:
            logger.error(
                "Batch embedding error",
                extra={
                    "error": str(e),
                    "batch_size": len(texts),
                    "model": self.model,
                }
            )
            raise EmbeddingError(
                f"Batch embedding error: {str(e)}",
                provider="siliconflow",
                model=self.model
            )
