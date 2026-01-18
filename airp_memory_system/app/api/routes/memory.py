"""
Memory management endpoints for AIRP system.
Week 5 Enhanced: Added deduplication, multi-strategy search, and entity management.
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.logger import get_logger
from app.models.requests import EpisodeInput, SearchRequest
from app.models.responses import EpisodeResult
from app.models.memory import SearchResult, EpisodeSummary, Entity, DeduplicationResult, SearchStrategy
from app.services.memory.graphiti_client import get_graphiti_client, GraphitiClient
from app.services.memory.entity_manager import EntityManager
from app.services.memory.deduplication_service import DeduplicationService
from app.core.exceptions import EpisodeError, SearchError, ValidationError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.post("/episodes", status_code=status.HTTP_201_CREATED, response_model=EpisodeSummary)
async def add_episode(
    episode_data: EpisodeInput,
    enable_deduplication: bool = Query(default=True, description="Enable duplicate detection")
):
    """
    Add a new episode to the knowledge graph (Week 5 Enhanced).

    This endpoint will:
    - Accept episode data (text or structured)
    - Check for duplicates if deduplication is enabled
    - Extract entities and relationships using Graphiti
    - Store in Neo4j with temporal metadata

    Args:
        episode_data: Episode input data
        enable_deduplication: Whether to check for duplicates (default: True)

    Returns:
        EpisodeSummary with entity and relationship counts

    Raises:
        422: Validation error
        500: Episode creation failed
    """
    try:
        # Get Graphiti client
        graphiti_client = await get_graphiti_client()

        # Add episode to Graphiti with deduplication support
        result = await graphiti_client.add_episode(
            name=episode_data.name,
            episode_body=episode_data.episode_body,
            source=episode_data.source,
            source_description=episode_data.source_description,
            reference_time=episode_data.reference_time,
            group_id=episode_data.group_id,
            metadata=episode_data.metadata,
            enable_deduplication=enable_deduplication
        )

        return result

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except EpisodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create episode: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error in add_episode", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: str):
    """
    Get an episode by ID.

    Args:
        episode_id: Episode UUID

    Returns:
        Episode details with entities and relationships

    Raises:
        404: Episode not found
        422: Invalid UUID format
        500: Server error
    """
    try:
        # Validate UUID format
        uuid_obj = UUID(episode_id)

        # Get Graphiti client
        graphiti_client = await get_graphiti_client()

        # Retrieve episode using Graphiti's get_nodes_and_edges_by_episode
        results = await graphiti_client.client.get_nodes_and_edges_by_episode(
            episode_uuid=episode_id
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )

        # Parse results
        entities = [
            {
                "uuid": str(node.uuid) if hasattr(node, 'uuid') else "",
                "name": node.name if hasattr(node, 'name') else "",
                "entity_type": node.label if hasattr(node, 'label') else "",
            }
            for node in results.get("nodes", [])
        ]

        relationships = [
            {
                "uuid": str(edge.uuid) if hasattr(edge, 'uuid') else "",
                "fact": edge.fact if hasattr(edge, 'fact') else "",
                "source_entity": edge.source_node_name if hasattr(edge, 'source_node_name') else "",
                "target_entity": edge.target_node_name if hasattr(edge, 'target_node_name') else "",
                "relationship_type": edge.label if hasattr(edge, 'label') else "",
            }
            for edge in results.get("edges", [])
        ]

        return {
            "uuid": episode_id,
            "name": results.get("episode_name", ""),
            "created_at": results.get("created_at", datetime.now()),
            "entities_count": len(entities),
            "relationships_count": len(relationships),
            "entities": entities,
            "relationships": relationships,
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving episode", extra={"error": str(e), "episode_id": episode_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve episode"
        )


@router.post("/search", response_model=List[SearchResult])
async def search_memory(search_data: SearchRequest):
    """
    Search the knowledge graph (Week 5 Enhanced).

    This endpoint will:
    - Accept natural language queries
    - Perform multi-strategy search (vector, keyword, graph, hybrid)
    - Return relevant facts and entities with relevance scores

    Args:
        search_data: Search request with query, strategy, and filters

    Returns:
        List of SearchResult objects with relevance scores

    Raises:
        422: Validation error
        500: Search failed
    """
    try:
        # Get Graphiti client
        graphiti_client = await get_graphiti_client()

        # Extract strategy from request (default to HYBRID)
        strategy = search_data.strategy or SearchStrategy.HYBRID

        # Execute search with strategy
        results = await graphiti_client.search(
            query=search_data.query,
            num_results=search_data.num_results,
            strategy=strategy,
            filters=search_data.filters
        )

        return results

    except SearchError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error in search_memory", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search"
        )


@router.get("/entities/{entity_id}", response_model=Entity)
async def get_entity(entity_id: str):
    """
    Get an entity by ID (Week 5 Enhanced).

    Args:
        entity_id: Entity UUID

    Returns:
        Entity with metadata

    Raises:
        404: Entity not found
        422: Invalid UUID format
        500: Server error
    """
    try:
        # Get Graphiti client
        graphiti_client = await get_graphiti_client()

        # Create EntityManager
        entity_manager = EntityManager(graphiti_client)

        # Get entity
        entity = await entity_manager.get_entity(entity_id)

        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found"
            )

        return entity

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving entity", extra={"error": str(e), "entity_id": entity_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity"
        )


@router.get("/entities")
async def list_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    List all entities with optional filtering (Week 5 Enhanced).

    Query Parameters:
        - entity_type: Filter by entity type
        - limit: Maximum number of results
        - offset: Pagination offset

    Returns:
        List of entities

    Raises:
        500: Server error
    """
    try:
        # Get Graphiti client
        graphiti_client = await get_graphiti_client()

        # Create EntityManager
        entity_manager = EntityManager(graphiti_client)

        # Filter by type if specified
        if entity_type:
            entities = await entity_manager.find_entities_by_type(entity_type)
        else:
            # Get all entities from cache (limited implementation)
            entities = list(entity_manager._entity_cache.values())

        # Apply pagination
        paginated_entities = entities[offset:offset + limit]

        return paginated_entities

    except Exception as e:
        logger.error("Error listing entities", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list entities"
        )


@router.post("/entities/check-duplicate", response_model=DeduplicationResult)
async def check_entity_duplicate(
    name: str = Query(..., description="Entity name"),
    entity_type: str = Query(..., description="Entity type"),
    description: str = Query("", description="Entity description")
):
    """
    Check if an entity is a duplicate (Week 5 New).

    This endpoint uses similarity scoring to detect potential duplicate entities
    before they are created.

    Args:
        name: Entity name
        entity_type: Entity type
        description: Entity description

    Returns:
        DeduplicationResult with similarity score and duplicate status

    Raises:
        500: Server error
    """
    try:
        # Get Graphiti client
        graphiti_client = await get_graphiti_client()

        # Use DeduplicationService
        if graphiti_client.dedup_service:
            result = await graphiti_client.dedup_service.check_entity_duplicate(
                name=name,
                entity_type=entity_type,
                description=description
            )
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Deduplication service not available"
            )

    except Exception as e:
        logger.error("Error checking entity duplicate", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check entity duplicate"
        )
