"""
Graphiti client wrapper for Neo4j temporal knowledge graph.
Based on Graphiti framework best practices.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import time

from app.core.logger import get_logger
from app.core.exceptions import (
    GraphitiConnectionError,
    EpisodeError,
    SearchError,
)
from app.core.config import settings
from app.models.memory import EpisodeSummary, SearchResult, SearchStrategy, Entity, Relationship

logger = get_logger(__name__)


class GraphitiClient:
    """
    Graphiti client wrapper for AIRP Memory System.

    This class provides a high-level interface to Graphiti's temporal
    knowledge graph capabilities, handling:
    - Neo4j connection management
    - Episode ingestion
    - Memory search
    - Entity and relationship management

    Attributes:
        client: Graphiti client instance
        config: Configuration settings

    TODO: Full implementation in Week 2
    """

    def __init__(self):
        """Initialize Graphiti client.

        Raises:
            GraphitiConnectionError: If connection fails
        """
        self.client = None
        self.config = settings

        # Week 5: Initialize services (lazy initialization in initialize())
        self.dedup_service = None
        self.search_service = None
        self.entity_manager = None
        self.embedding_client = None
        self.reranker_client = None

        logger.info(
            "Graphiti client initialization",
            extra={
                "neo4j_uri": self.config.neo4j_uri,
                "database": self.config.neo4j_database,
            }
        )

    async def initialize(self) -> None:
        """
        Initialize Neo4j connection and build indices.

        This method:
        1. Creates LLM client configuration for DeepSeek
        2. Creates embedder configuration for SiliconFlow
        3. Initializes Graphiti client with custom LLM/embedder
        4. Builds necessary indices and constraints

        Raises:
            GraphitiConnectionError: If initialization fails
        """
        try:
            # Import Graphiti dependencies
            from graphiti_core import Graphiti
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
            from graphiti_core.nodes import EpisodeType

            # Import custom DeepSeek client for structured output support
            from app.services.llm.deepseek_graphiti_client import DeepSeekGraphitiClient

            # Step 1: Configure custom LLM client (DeepSeek with structured output support)
            llm_client = DeepSeekGraphitiClient(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url,
                model=self.config.graphiti_llm_model,
            )

            # Step 2: Configure embedder (SiliconFlow-compatible)
            # Note: embedding_dim is not set because SiliconFlow API doesn't support
            # the dimensions parameter for BAAI/bge-m3 model (only Qwen/Qwen3 series)
            embedder = OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key=self.config.siliconflow_api_key,
                    embedding_model=self.config.graphiti_embedding_model,
                    base_url=self.config.siliconflow_base_url,
                )
            )

            # Step 4: Initialize Graphiti
            # Note: Using minimal configuration to avoid type errors
            self.client = Graphiti(
                uri=self.config.neo4j_uri,
                user=self.config.neo4j_user,
                password=self.config.neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
            )

            # Step 5: Build indices and constraints
            if self.config.graphiti_enable_indices:
                await self.client.build_indices_and_constraints()
                logger.info("Graphiti indices and constraints built successfully")

            logger.info(
                "Graphiti client initialized successfully",
                extra={
                    "neo4j_uri": self.config.neo4j_uri,
                    "database": self.config.neo4j_database,
                    "llm_model": self.config.graphiti_llm_model,
                    "embedding_model": self.config.graphiti_embedding_model,
                }
            )

            # Week 5: Initialize Week 5 services
            from app.services.llm.embedding_client import EmbeddingClient
            from app.services.llm.reranker_client import RerankerClient
            from app.services.memory.deduplication_service import DeduplicationService
            from app.services.memory.entity_manager import EntityManager

            self.embedding_client = EmbeddingClient()
            self.reranker_client = RerankerClient()
            self.dedup_service = DeduplicationService(self.embedding_client)
            self.entity_manager = EntityManager(self)

            logger.info("Week 5 services initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Graphiti client", extra={"error": str(e)})
            raise GraphitiConnectionError(f"Failed to connect to Neo4j: {str(e)}")

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        source: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        group_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        enable_deduplication: bool = True
    ) -> EpisodeSummary:
        """
        Add an episode to the knowledge graph with optional deduplication.

        Args:
            name: Episode name
            episode_body: Episode content
            source: Source type (text, json, etc.)
            source_description: Optional source description
            reference_time: Reference timestamp
            group_id: Optional group ID for episodes
            metadata: Optional metadata
            enable_deduplication: Whether to check for duplicates (default: True)

        Returns:
            EpisodeSummary with entity and relationship counts

        Raises:
            EpisodeError: If episode creation fails
        """
        if not self.client:
            raise GraphitiConnectionError("Graphiti client not initialized")

        try:
            # Week 5: Deduplication check
            if enable_deduplication and self.dedup_service:
                dedup_result = await self.dedup_service.check_episode_duplicate(episode_body)
                if dedup_result.is_duplicate:
                    logger.info(
                        "Duplicate episode detected",
                        extra={
                            "name": name,
                            "matched_uuid": dedup_result.matched_uuid,
                            "similarity": dedup_result.similarity_score
                        }
                    )
                    # Return existing episode info
                    return EpisodeSummary(
                        episode_uuid=dedup_result.matched_uuid or "",
                        name=name,
                        content_summary=episode_body[:200] + "..." if len(episode_body) > 200 else episode_body,
                        entity_count=0,
                        relationship_count=0
                    )

            # Import EpisodeType
            from graphiti_core.nodes import EpisodeType

            # Normalize reference_time
            if reference_time is None:
                reference_time = datetime.now(timezone.utc)
            elif reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)

            # Map source string to EpisodeType enum
            source_map = {
                "text": EpisodeType.text,
                "message": EpisodeType.message,
                "json": EpisodeType.json,
            }
            episode_type = source_map.get(source.lower(), EpisodeType.text)

            # Prepare source_description from metadata or use default
            source_description = metadata.get("source_description", "") if metadata else ""

            logger.info(
                "Adding episode to Graphiti",
                extra={
                    "name": name,
                    "source": source,
                    "source_description": source_description,
                    "group_id": group_id,
                    "episode_body_length": len(episode_body),
                    "episode_type": str(episode_type),
                    "episode_type_value": episode_type.value if hasattr(episode_type, 'value') else str(episode_type),
                    "reference_time": str(reference_time),
                }
            )

            # Call Graphiti's add_episode
            result = await self.client.add_episode(
                name=name,
                episode_body=episode_body,
                source_description=source_description,
                reference_time=reference_time,
                source=episode_type,
                group_id=group_id or "",
            )

            # Extract results
            # AddEpisodeResults has: episode (EpisodicNode), nodes (list[EntityNode]), edges (list[EntityEdge])
            entities = []
            relationships = []

            # Create a mapping from node UUID to node name
            node_name_map = {}
            if hasattr(result, 'nodes'):
                for node in result.nodes:
                    node_uuid = str(node.uuid) if hasattr(node, 'uuid') else ""
                    node_name = node.name if hasattr(node, 'name') else ""

                    # Store entity data
                    entity = {
                        "uuid": node_uuid,
                        "name": node_name,
                        "entity_type": node.label if hasattr(node, 'label') else "",
                    }
                    entities.append(entity)

                    # Create mapping for edges
                    if node_uuid:
                        node_name_map[node_uuid] = node_name

            # Extract relationships from edges
            if hasattr(result, 'edges'):
                for edge in result.edges:
                    # Get source and target node names from UUIDs
                    source_uuid = str(edge.source_node_uuid) if hasattr(edge, 'source_node_uuid') else ""
                    target_uuid = str(edge.target_node_uuid) if hasattr(edge, 'target_node_uuid') else ""

                    # Get relationship type and fact from edge
                    rel_type = edge.name if hasattr(edge, 'name') else ""
                    fact = edge.fact if hasattr(edge, 'fact') else ""

                    relationship = {
                        "uuid": str(edge.uuid) if hasattr(edge, 'uuid') else "",
                        "source_entity": node_name_map.get(source_uuid, ""),
                        "target_entity": node_name_map.get(target_uuid, ""),
                        "relationship_type": rel_type,
                        "fact": fact,
                        "source_entity_uuid": source_uuid,
                        "target_entity_uuid": target_uuid,
                    }
                    relationships.append(relationship)

            # Get episode UUID from result.episode
            episode_uuid = ""
            if hasattr(result, 'episode'):
                episode_uuid = str(result.episode.uuid) if hasattr(result.episode, 'uuid') else ""
            elif hasattr(result, 'episode_uuid'):
                episode_uuid = str(result.episode_uuid)

            logger.info(
                "Episode added successfully",
                extra={
                    "episode_uuid": episode_uuid,
                    "entities_count": len(entities),
                    "relationships_count": len(relationships),
                    "has_nodes": hasattr(result, 'nodes'),
                    "has_edges": hasattr(result, 'edges'),
                }
            )

            # Week 5: Track episode embedding for deduplication
            if self.dedup_service:
                await self.dedup_service.add_episode_embedding(episode_uuid, episode_body)

            # Week 5: Return EpisodeSummary instead of Dict
            return EpisodeSummary(
                episode_uuid=episode_uuid,
                name=name,
                content_summary=episode_body[:200] + "..." if len(episode_body) > 200 else episode_body,
                entity_count=len(entities),
                relationship_count=len(relationships)
            )

        except Exception as e:
            logger.error("Failed to add episode", extra={"error": str(e), "name": name})
            raise EpisodeError(f"Failed to add episode '{name}': {str(e)}")

    async def search(
        self,
        query: str,
        num_results: int = 10,
        strategy: SearchStrategy = SearchStrategy.HYBRID,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search the knowledge graph using specified strategy.

        Args:
            query: Search query
            num_results: Number of results to return
            strategy: Search strategy (vector, keyword, graph, hybrid)
            filters: Optional search filters

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If search fails
        """
        if not self.client:
            raise GraphitiConnectionError("Graphiti client not initialized")

        # Week 5: Use SearchService for enhanced search capabilities
        if strategy != SearchStrategy.HYBRID or filters is not None:
            # Lazy initialize SearchService if needed
            if self.search_service is None:
                from app.services.memory.search_service import SearchService
                self.search_service = SearchService(self, self.reranker_client)

            # Delegate to SearchService
            return await self.search_service.search(
                query=query,
                strategy=strategy,
                num_results=num_results,
                filters=filters
            )

        # Fall back to original Graphiti search for HYBRID strategy without filters
        try:
            start_time = time.time()

            # Extract filters
            group_ids = filters.get("group_ids") if filters else None
            center_node_uuid = filters.get("center_node_uuid") if filters else None

            logger.info(
                "Executing Graphiti search",
                extra={
                    "query": query,
                    "num_results": num_results,
                    "has_filters": filters is not None,
                }
            )

            # Execute search using Graphiti's hybrid search
            results = await self.client.search(
                query=query,
                num_results=num_results,
                group_ids=group_ids,
                center_node_uuid=center_node_uuid,
            )

            search_time = time.time() - start_time

            # Parse results into facts and entities
            facts = []
            entities = set()  # Use set to deduplicate

            # Collect all node UUIDs from edges for batch lookup
            node_uuids = set()
            for edge in results:
                if hasattr(edge, 'source_node_uuid'):
                    node_uuids.add(edge.source_node_uuid)
                if hasattr(edge, 'target_node_uuid'):
                    node_uuids.add(edge.target_node_uuid)

            # Lookup node names for all unique UUIDs
            node_name_map = {}
            if node_uuids:
                from neo4j import AsyncGraphDatabase
                driver = AsyncGraphDatabase.driver(
                    self.config.neo4j_uri,
                    auth=(self.config.neo4j_user, self.config.neo4j_password)
                )
                try:
                    async with driver.session(database=self.config.neo4j_database) as session:
                        # Query all node names in one batch
                        neo4j_query = """
                            MATCH (n:Entity)
                            WHERE n.uuid IN $node_uuids
                            RETURN n.uuid AS uuid, n.name AS name
                        """
                        result = await session.run(neo4j_query, node_uuids=list(node_uuids))
                        async for record in result:
                            node_name_map[record["uuid"]] = record["name"]
                finally:
                    await driver.close()

            for edge in results:
                # Get source and target node names from UUIDs
                source_uuid = str(edge.source_node_uuid) if hasattr(edge, 'source_node_uuid') else ""
                target_uuid = str(edge.target_node_uuid) if hasattr(edge, 'target_node_uuid') else ""
                source_name = node_name_map.get(source_uuid, "")
                target_name = node_name_map.get(target_uuid, "")

                # Get relationship type from edge.name
                relationship_type = edge.name if hasattr(edge, 'name') else ""

                # Extract fact (edge information)
                fact = {
                    "uuid": str(edge.uuid) if hasattr(edge, 'uuid') else "",
                    "fact": edge.fact if hasattr(edge, 'fact') else "",
                    "source_entity": source_name,
                    "target_entity": target_name,
                    "relationship_type": relationship_type,
                    "created_at": edge.created_at if hasattr(edge, 'created_at') else None,
                    "valid_at": edge.valid_at if hasattr(edge, 'valid_at') else None,
                    "expired_at": edge.expired_at if hasattr(edge, 'expired_at') else None,
                }
                facts.append(fact)

                # Extract entities
                if source_name:
                    entities.add(source_name)
                if target_name:
                    entities.add(target_name)

            logger.info(
                "Search completed successfully",
                extra={
                    "query": query,
                    "results_count": len(facts),
                    "unique_entities": len(entities),
                    "search_time": search_time,
                }
            )

            # Week 5: Convert facts to SearchResult format
            results = []
            for i, fact in enumerate(facts):
                # Calculate score based on position (earlier = higher score)
                score = 1.0 - (i / len(facts)) if len(facts) > 0 else 0.0

                # Format fact content
                content = f"{fact.get('source_entity', '')} {fact.get('relationship_type', '')} {fact.get('target_entity', '')}"
                if fact.get('fact'):
                    content += f": {fact['fact']}"

                result = SearchResult(
                    uuid=fact.get('uuid', f"{query}-{i}"),
                    content=content,
                    score=score,
                    metadata={
                        "fact": fact.get('fact', ''),
                        "relationship_type": fact.get('relationship_type', ''),
                        "created_at": str(fact.get('created_at', '')),
                        "search_time": search_time
                    },
                    entity_uuids=[
                        fact.get('source_entity_uuid', ''),
                        fact.get('target_entity_uuid', '')
                    ]
                )
                results.append(result)

            return results

        except Exception as e:
            logger.error("Search failed", extra={"error": str(e), "query": query})
            raise SearchError(
                f"Search failed for query '{query}': {str(e)}",
                query=query,
                filters=filters
            )

    async def _extract_entities(self, content: str) -> List[Entity]:
        """Extract entities from episode content.

        TODO: Implement with LLM-based entity extraction.
        For now, returns empty list.

        Args:
            content: Episode content

        Returns:
            List of extracted entities
        """
        # TODO: Use LLM to extract entities from content
        # Example: Use DeepSeekClient to identify entities
        logger.debug("_extract_entities not yet implemented with LLM")
        return []

    async def _extract_relationships(self, content: str) -> List[Relationship]:
        """Extract relationships from episode content.

        TODO: Implement with LLM-based relationship extraction.
        For now, returns empty list.

        Args:
            content: Episode content

        Returns:
            List of extracted relationships
        """
        # TODO: Use LLM to extract relationships from content
        # Example: Use DeepSeekClient to identify relationships
        logger.debug("_extract_relationships not yet implemented with LLM")
        return []

    async def close(self) -> None:
        """Close Neo4j connection and cleanup resources."""
        if self.client:
            try:
                await self.client.close()
                logger.info("Graphiti client closed successfully")
            except Exception as e:
                logger.error("Error closing Graphiti client", extra={"error": str(e)})


# Global client instance
_graphiti_client: Optional[GraphitiClient] = None


async def get_graphiti_client() -> GraphitiClient:
    """
    Get or create Graphiti client singleton.

    Returns:
        Graphiti client instance

    Raises:
        GraphitiConnectionError: If client creation fails
    """
    global _graphiti_client

    if _graphiti_client is None:
        _graphiti_client = GraphitiClient()
        await _graphiti_client.initialize()

    return _graphiti_client
