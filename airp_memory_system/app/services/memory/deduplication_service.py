"""Deduplication Service for Week 5.

This service provides duplicate detection and prevention for entities and episodes
using similarity scoring with embeddings.
"""

from typing import Optional, List, Tuple, Dict, Any
import numpy as np

from app.core.logger import get_logger
from app.models.memory import Entity, DeduplicationResult
from app.services.llm.embedding_client import EmbeddingClient
from app.core.config import settings

logger = get_logger(__name__)


class DeduplicationService:
    """Detect and prevent duplicate entities and episodes.

    This service uses embedding-based similarity to detect potential duplicates
    before they are created, helping maintain data quality in the knowledge graph.

    Attributes:
        embedding_client: EmbeddingClient instance for generating embeddings
        threshold: Similarity threshold for duplicate detection (default: 0.85)
        name_weight: Weight for entity name similarity (default: 0.4)
        description_weight: Weight for entity description similarity (default: 0.6)
    """

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        threshold: Optional[float] = None,
        name_weight: Optional[float] = None,
        description_weight: Optional[float] = None
    ):
        """Initialize DeduplicationService.

        Args:
            embedding_client: EmbeddingClient instance for generating embeddings
            threshold: Similarity threshold (0-1), defaults to config value
            name_weight: Weight for name similarity in entity comparison
            description_weight: Weight for description similarity in entity comparison
        """
        self.embedding_client = embedding_client

        # Use config values if not provided
        self.threshold = threshold or settings.deduplication_similarity_threshold
        self.name_weight = name_weight or settings.deduplication_entity_name_weight
        self.description_weight = description_weight or settings.deduplication_entity_description_weight

        # In-memory storage for checking duplicates (in production, would query Graphiti)
        self._entity_embeddings: Dict[str, np.ndarray] = {}
        self._episode_embeddings: Dict[str, np.ndarray] = {}

    async def check_entity_duplicate(
        self,
        name: str,
        entity_type: str,
        description: str = ""
    ) -> DeduplicationResult:
        """Check if an entity is a duplicate of existing entities.

        Combines name similarity and description embedding similarity
        to determine if an entity is likely a duplicate.

        Args:
            name: Entity name
            entity_type: Entity type (person, location, etc.)
            description: Entity description

        Returns:
            DeduplicationResult with is_duplicate flag and similarity score
        """
        try:
            logger.info(f"Checking entity duplicate: {name} (type: {entity_type})")

            # TODO: Query existing entities from Graphiti
            # For now, check against in-memory cache
            if not self._entity_embeddings:
                logger.debug("No existing entities to check against")
                return DeduplicationResult(
                    is_duplicate=False,
                    similarity_score=0.0,
                    matched_uuid=None,
                    match_reason="No existing entities of this type"
                )

            # Generate embedding for the new entity description
            new_embedding = await self.embedding_client.generate_embedding(
                f"{name} {description}".strip()
            )

            # Check similarity against existing entities
            best_match_uuid = None
            best_similarity = 0.0
            best_match_reason = ""

            for existing_uuid, existing_embedding in self._entity_embeddings.items():
                # Calculate cosine similarity
                similarity = self._cosine_similarity(new_embedding, existing_embedding)

                # Add name similarity (simple exact/fuzzy match for now)
                # TODO: Could use embedding similarity for names too
                name_similarity = self._name_similarity(name, existing_uuid)

                # Combined similarity score
                combined_score = (
                    name_similarity * self.name_weight +
                    similarity * self.description_weight
                )

                if combined_score > best_similarity:
                    best_similarity = combined_score
                    best_match_uuid = existing_uuid
                    best_match_reason = (
                        f"Combined similarity: {combined_score:.3f} "
                        f"(name: {name_similarity:.3f}, description: {similarity:.3f})"
                    )

            # Determine if duplicate based on threshold
            is_duplicate = best_similarity >= self.threshold

            if is_duplicate:
                logger.info(f"Duplicate entity detected: {name} -> {best_match_uuid} "
                          f"(similarity: {best_similarity:.3f})")
            else:
                logger.debug(f"Entity {name} is not a duplicate (best similarity: {best_similarity:.3f})")

            return DeduplicationResult(
                is_duplicate=is_duplicate,
                similarity_score=best_similarity,
                matched_uuid=best_match_uuid if is_duplicate else None,
                match_reason=best_match_reason
            )

        except Exception as e:
            logger.error(f"Failed to check entity duplicate: {e}")
            raise

    async def check_episode_duplicate(self, content: str) -> DeduplicationResult:
        """Check if an episode is a duplicate of existing episodes.

        Uses content embedding similarity to detect duplicate episodes.

        Args:
            content: Episode content to check

        Returns:
            DeduplicationResult with is_duplicate flag and similarity score
        """
        try:
            logger.info(f"Checking episode duplicate (content length: {len(content)})")

            # TODO: Query existing episodes from Graphiti
            # For now, check against in-memory cache
            if not self._episode_embeddings:
                logger.debug("No existing episodes to check against")
                return DeduplicationResult(
                    is_duplicate=False,
                    similarity_score=0.0,
                    matched_uuid=None,
                    match_reason="No existing episodes"
                )

            # Generate embedding for the new episode
            new_embedding = await self.embedding_client.generate_embedding(content)

            # Find best match
            best_match_uuid = None
            best_similarity = 0.0

            for existing_uuid, existing_embedding in self._episode_embeddings.items():
                similarity = self._cosine_similarity(new_embedding, existing_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_uuid = existing_uuid

            # Determine if duplicate based on threshold
            is_duplicate = best_similarity >= self.threshold

            if is_duplicate:
                logger.info(f"Duplicate episode detected -> {best_match_uuid} "
                          f"(similarity: {best_similarity:.3f})")
            else:
                logger.debug(f"Episode is not a duplicate (best similarity: {best_similarity:.3f})")

            return DeduplicationResult(
                is_duplicate=is_duplicate,
                similarity_score=best_similarity,
                matched_uuid=best_match_uuid if is_duplicate else None,
                match_reason=f"Content similarity: {best_similarity:.3f}"
            )

        except Exception as e:
            logger.error(f"Failed to check episode duplicate: {e}")
            raise

    async def find_similar_entities(
        self,
        entity: Entity,
        threshold: Optional[float] = None
    ) -> List[Tuple[Entity, float]]:
        """Find entities similar to the given entity above the threshold.

        Args:
            entity: Entity to find similar entities for
            threshold: Minimum similarity threshold (defaults to instance threshold)

        Returns:
            List of (Entity, similarity_score) tuples, sorted by similarity
        """
        try:
            logger.info(f"Finding entities similar to: {entity.name}")

            search_threshold = threshold or self.threshold

            # TODO: Query entities from Graphiti
            # For now, return empty list
            logger.warning("find_similar_entities not fully implemented (requires Graphiti query)")
            return []

        except Exception as e:
            logger.error(f"Failed to find similar entities: {e}")
            return []

    async def suggest_entity_merge(
        self,
        entity_uuids: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate merge suggestions for a list of entities.

        Analyzes entities and suggests which ones should be merged based on
        similarity scores and metadata.

        Args:
            entity_uuids: List of entity UUIDs to analyze

        Returns:
            List of merge suggestions with similarity scores and recommended actions
        """
        try:
            logger.info(f"Generating merge suggestions for {len(entity_uuids)} entities")

            # TODO: Implement merge suggestion logic
            # Should:
            # 1. Fetch all entities by UUID
            # 2. Calculate pairwise similarities
            # 3. Group entities above threshold
            # 4. Recommend merge strategy (keep newest, merge metadata, etc.)

            logger.warning("suggest_entity_merge not fully implemented")
            return []

        except Exception as e:
            logger.error(f"Failed to generate merge suggestions: {e}")
            return []

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Convert to numpy arrays if needed
            v1 = np.array(vec1) if not isinstance(vec1, np.ndarray) else vec1
            v2 = np.array(vec2) if not isinstance(vec2, np.ndarray) else vec2

            # Calculate cosine similarity
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Clamp to [0, 1] range
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

    def _name_similarity(self, name1: str, name2_or_uuid: str) -> float:
        """Calculate simple name similarity.

        TODO: Enhance with fuzzy matching or embedding-based similarity.

        Args:
            name1: First name
            name2_or_uuid: Second name or UUID (for mock implementation)

        Returns:
            Similarity score (0-1)
        """
        try:
            # For mock implementation, if name2_or_uuid is a UUID, return 0
            if len(name2_or_uuid) == 36 and name2_or_uuid.count('-') == 4:
                return 0.0

            name2 = name2_or_uuid

            # Simple exact match
            if name1.lower() == name2.lower():
                return 1.0

            # Simple substring match
            if name1.lower() in name2.lower() or name2.lower() in name1.lower():
                return 0.7

            # No match
            return 0.0

        except Exception as e:
            logger.error(f"Failed to calculate name similarity: {e}")
            return 0.0

    async def add_entity_embedding(self, uuid: str, name: str, description: str):
        """Add an entity embedding to the cache.

        TODO: This will be replaced by Graphiti queries in production.

        Args:
            uuid: Entity UUID
            name: Entity name
            description: Entity description
        """
        try:
            text = f"{name} {description}".strip()
            embedding = await self.embedding_client.generate_embedding(text)
            self._entity_embeddings[uuid] = np.array(embedding)
            logger.debug(f"Added embedding for entity: {uuid}")

        except Exception as e:
            logger.error(f"Failed to add entity embedding: {e}")

    async def add_episode_embedding(self, uuid: str, content: str):
        """Add an episode embedding to the cache.

        TODO: This will be replaced by Graphiti queries in production.

        Args:
            uuid: Episode UUID
            content: Episode content
        """
        try:
            embedding = await self.embedding_client.generate_embedding(content)
            self._episode_embeddings[uuid] = np.array(embedding)
            logger.debug(f"Added embedding for episode: {uuid}")

        except Exception as e:
            logger.error(f"Failed to add episode embedding: {e}")
