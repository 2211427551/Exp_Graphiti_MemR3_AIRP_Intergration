"""Search Service for Week 5.

This service provides enhanced search capabilities with multiple strategies:
- Vector search: Semantic similarity using embeddings
- Keyword search: Text-based matching
- Graph traversal: Relationship-based exploration
- Hybrid search: Combines multiple strategies with weighted scoring
"""

from typing import Optional, List, Dict, Any, Tuple
import numpy as np

from app.core.logger import get_logger
from app.models.memory import SearchStrategy, SearchResult
from app.services.memory.graphiti_client import GraphitiClient
from app.services.llm.reranker_client import RerankerClient

logger = get_logger(__name__)


class SearchService:
    """Enhanced search service with multiple strategies.

    This service provides flexible search capabilities across the knowledge graph,
    supporting vector similarity, keyword matching, graph traversal, and hybrid approaches.

    Attributes:
        graphiti_client: GraphitiClient instance for graph operations
        reranker_client: RerankerClient instance for result reranking
    """

    def __init__(
        self,
        graphiti_client: GraphitiClient,
        reranker_client: RerankerClient
    ):
        """Initialize SearchService.

        Args:
            graphiti_client: GraphitiClient instance for graph operations
            reranker_client: RerankerClient instance for result reranking
        """
        self.graphiti_client = graphiti_client
        self.reranker_client = reranker_client

    async def search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.HYBRID,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search memory using specified strategy.

        Args:
            query: Search query text
            strategy: Search strategy to use
            num_results: Number of results to return
            filters: Optional search filters

        Returns:
            List of SearchResult objects, sorted by relevance (highest first)

        Raises:
            ValueError: If strategy is invalid
        """
        logger.info(f"Searching with strategy={strategy}, query={query[:50]}...")

        try:
            # Handle string strategy (convert to enum if possible)
            if isinstance(strategy, str):
                try:
                    strategy = SearchStrategy(strategy)
                except ValueError:
                    raise ValueError(f"Invalid search strategy: {strategy}")

            if strategy == SearchStrategy.VECTOR:
                return await self.vector_search(query, num_results, **(filters or {}))
            elif strategy == SearchStrategy.KEYWORD:
                return await self.keyword_search(query, num_results, **(filters or {}))
            elif strategy == SearchStrategy.GRAPH_TRAVERSAL:
                # Graph traversal requires a seed entity UUID from filters
                entity_uuid = filters.get('entity_uuid') if filters else None
                if not entity_uuid:
                    logger.warning("Graph traversal requires entity_uuid in filters")
                    return []
                # Remove entity_uuid from filters to avoid duplicate argument
                safe_filters = (filters or {}).copy()
                safe_filters.pop('entity_uuid', None)
                return await self.graph_traversal_search(
                    entity_uuid,
                    num_results,
                    **safe_filters
                )
            elif strategy == SearchStrategy.HYBRID:
                # Extract hybrid weights from filters or use defaults
                vector_weight = filters.get('vector_weight', 0.6) if filters else 0.6
                keyword_weight = filters.get('keyword_weight', 0.3) if filters else 0.3
                graph_weight = filters.get('graph_weight', 0.1) if filters else 0.1
                return await self.hybrid_search(
                    query,
                    num_results,
                    vector_weight,
                    keyword_weight,
                    graph_weight
                )
            else:
                raise ValueError(f"Invalid search strategy: {strategy}")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise  # Re-raise exception to be handled by caller

    async def vector_search(
        self,
        query: str,
        num_results: int = 10,
        **filters
    ) -> List[SearchResult]:
        """Perform semantic vector search using embeddings.

        Args:
            query: Search query text
            num_results: Number of results to return
            **filters: Additional filters (entity_types, date_range, etc.)

        Returns:
            List of SearchResult objects with relevance scores
        """
        try:
            logger.info(f"Vector search: {query[:50]}...")

            # Generate query embedding
            query_embedding = await self.graphiti_client.embedding_client.generate_embedding(
                query
            )

            # TODO: Call Graphiti search with embedding
            # For now, return mock results
            results = self._create_mock_vector_results(query, num_results)

            logger.info(f"Vector search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def keyword_search(
        self,
        query: str,
        num_results: int = 10,
        **filters
    ) -> List[SearchResult]:
        """Perform text-based keyword search.

        Args:
            query: Search query text
            num_results: Number of results to return
            **filters: Additional filters

        Returns:
            List of SearchResult objects with relevance scores
        """
        try:
            logger.info(f"Keyword search: {query[:50]}...")

            # TODO: Implement full-text search with BM25 or similar
            # For now, use simple text containment matching
            results = self._create_mock_keyword_results(query, num_results)

            logger.info(f"Keyword search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    async def graph_traversal_search(
        self,
        entity_uuid: str,
        max_depth: int = 2,
        num_results: int = 10,
        **filters
    ) -> List[SearchResult]:
        """Perform graph relationship traversal search.

        Args:
            entity_uuid: Starting entity UUID for traversal
            max_depth: Maximum traversal depth (default: 2)
            num_results: Number of results to return
            **filters: Additional filters

        Returns:
            List of SearchResult objects with relevance scores
        """
        try:
            logger.info(f"Graph traversal from entity: {entity_uuid}")

            # TODO: Implement BFS/DFS traversal on graph
            # For now, return mock results
            results = self._create_mock_graph_results(entity_uuid, num_results)

            logger.info(f"Graph traversal found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        num_results: int = 10,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.3,
        graph_weight: float = 0.1
    ) -> List[SearchResult]:
        """Perform hybrid search combining multiple strategies.

        Combines vector, keyword, and graph traversal results with weighted scoring.

        Args:
            query: Search query text
            num_results: Number of results to return
            vector_weight: Weight for vector search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)
            graph_weight: Weight for graph traversal results (0-1)

        Returns:
            List of combined and re-ranked SearchResult objects

        Raises:
            ValueError: If weights don't sum to approximately 1.0
        """
        logger.info(f"Hybrid search: {query[:50]}... (v={vector_weight}, k={keyword_weight}, g={graph_weight})")

        # Validate weights
        total_weight = vector_weight + keyword_weight + graph_weight
        if not (0.9 <= total_weight <= 1.1):  # Allow small floating point errors
            raise ValueError(f"Weights must sum to ~1.0, got {total_weight}")

        try:

            # Perform searches in parallel (conceptually)
            vector_results = await self.vector_search(query, num_results * 2)
            keyword_results = await self.keyword_search(query, num_results * 2)
            # Note: Graph traversal requires a seed entity, so we'll skip it for general queries
            # or use it only when an entity is provided

            # Combine and score results
            combined_scores: Dict[str, Tuple[SearchResult, float]] = {}

            # Add vector results
            for result in vector_results:
                combined_key = result.uuid
                if combined_key not in combined_scores:
                    combined_scores[combined_key] = (result, 0.0)
                combined_scores[combined_key] = (
                    combined_scores[combined_key][0],
                    combined_scores[combined_key][1] + result.score * vector_weight
                )

            # Add keyword results
            for result in keyword_results:
                combined_key = result.uuid
                if combined_key not in combined_scores:
                    combined_scores[combined_key] = (result, 0.0)
                combined_scores[combined_key] = (
                    combined_scores[combined_key][0],
                    combined_scores[combined_key][1] + result.score * keyword_weight
                )

            # Sort by combined score and return top results
            sorted_results = sorted(
                combined_scores.values(),
                key=lambda x: x[1],
                reverse=True
            )[:num_results]

            # Create final SearchResult objects with combined scores
            final_results = [
                SearchResult(
                    uuid=result.uuid,
                    content=result.content,
                    score=combined_score,
                    metadata=result.metadata,
                    entity_uuids=result.entity_uuids
                )
                for result, combined_score in sorted_results
            ]

            logger.info(f"Hybrid search found {len(final_results)} results")
            return final_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise  # Re-raise to be handled by caller

    def _create_mock_vector_results(
        self,
        query: str,
        num_results: int
    ) -> List[SearchResult]:
        """Create mock vector search results for testing.

        TODO: Replace with actual Graphiti vector search
        """
        import uuid
        results = []
        for i in range(min(num_results, 5)):
            score = 0.95 - (i * 0.1)  # Decreasing scores
            results.append(SearchResult(
                uuid=str(uuid.uuid4()),
                content=f"Vector search result {i+1} for: {query[:30]}...",
                score=max(0.0, min(1.0, score)),
                metadata={"strategy": "vector", "rank": i + 1}
            ))
        return results

    def _create_mock_keyword_results(
        self,
        query: str,
        num_results: int
    ) -> List[SearchResult]:
        """Create mock keyword search results for testing.

        TODO: Replace with actual full-text search implementation
        """
        import uuid
        results = []
        for i in range(min(num_results, 5)):
            score = 0.9 - (i * 0.15)  # Decreasing scores
            results.append(SearchResult(
                uuid=str(uuid.uuid4()),
                content=f"Keyword match {i+1} containing: {query[:30]}...",
                score=max(0.0, min(1.0, score)),
                metadata={"strategy": "keyword", "rank": i + 1}
            ))
        return results

    def _create_mock_graph_results(
        self,
        entity_uuid: str,
        num_results: int
    ) -> List[SearchResult]:
        """Create mock graph traversal results for testing.

        TODO: Replace with actual graph BFS/DFS traversal
        """
        import uuid
        results = []
        for i in range(min(num_results, 5)):
            score = 0.8 - (i * 0.12)  # Decreasing scores
            results.append(SearchResult(
                uuid=str(uuid.uuid4()),
                content=f"Related entity {i+1} connected to {entity_uuid[:8]}...",
                score=max(0.0, min(1.0, score)),
                metadata={"strategy": "graph", "rank": i + 1},
                entity_uuids=[entity_uuid]
            ))
        return results
