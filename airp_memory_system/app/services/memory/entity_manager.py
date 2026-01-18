"""Entity Manager service for Week 5.

This service provides CRUD operations for entities in the knowledge graph,
building on top of the Graphiti framework.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.logger import get_logger
from app.models.memory import Entity, Relationship
from app.services.memory.graphiti_client import GraphitiClient

logger = get_logger(__name__)


class EntityManager:
    """Manage entity CRUD operations in the knowledge graph.

    This service provides a high-level interface for creating, reading,
    updating, and deleting entities, as well as querying entities by
    various criteria.

    Attributes:
        graphiti_client: GraphitiClient instance for graph operations
    """

    def __init__(self, graphiti_client: GraphitiClient):
        """Initialize EntityManager.

        Args:
            graphiti_client: GraphitiClient instance for graph operations
        """
        self.graphiti_client = graphiti_client
        self._entity_cache: Dict[str, Entity] = {}

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        description: str = "",
        **metadata
    ) -> Entity:
        """Create a new entity in the knowledge graph.

        Args:
            name: Entity name
            entity_type: Entity type (e.g., person, location, organization)
            description: Entity description
            **metadata: Additional metadata as key-value pairs

        Returns:
            Created Entity object with assigned UUID

        Raises:
            Exception: If entity creation fails
        """
        try:
            logger.info(f"Creating entity: {name} (type: {entity_type})")

            # TODO: Call Graphiti API to create entity
            # For now, return a mock entity with a generated UUID
            import uuid
            entity_uuid = str(uuid.uuid4())

            entity = Entity(
                uuid=entity_uuid,
                name=name,
                entity_type=entity_type,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=metadata
            )

            # Cache the entity
            self._entity_cache[entity_uuid] = entity

            logger.info(f"Entity created successfully: {entity_uuid}")
            return entity

        except Exception as e:
            logger.error(f"Failed to create entity {name}: {e}")
            raise

    async def get_entity(self, uuid: str) -> Optional[Entity]:
        """Get an entity by UUID.

        Args:
            uuid: Entity UUID

        Returns:
            Entity object if found, None otherwise
        """
        try:
            # Check cache first
            if uuid in self._entity_cache:
                logger.debug(f"Entity {uuid} retrieved from cache")
                return self._entity_cache[uuid]

            # TODO: Query Graphiti for entity
            logger.info(f"Retrieving entity: {uuid}")

            # For now, return None (not implemented)
            logger.warning(f"Entity {uuid} not found")
            return None

        except Exception as e:
            logger.error(f"Failed to get entity {uuid}: {e}")
            return None

    async def update_entity(self, uuid: str, **updates) -> Optional[Entity]:
        """Update an entity.

        Args:
            uuid: Entity UUID
            **updates: Fields to update (name, description, metadata, etc.)

        Returns:
            Updated Entity object if successful, None otherwise
        """
        try:
            logger.info(f"Updating entity: {uuid}")

            # Get existing entity
            entity = await self.get_entity(uuid)
            if not entity:
                logger.warning(f"Cannot update non-existent entity: {uuid}")
                return None

            # Separate metadata from other fields
            metadata_updates = {}
            field_updates = {}
            for key, value in updates.items():
                # Known Entity fields
                if key in ['name', 'entity_type', 'description', 'uuid', 'created_at', 'updated_at']:
                    field_updates[key] = value
                else:
                    # Everything else goes into metadata
                    metadata_updates[key] = value

            # Update fields
            update_data = entity.model_dump()
            update_data.update(field_updates)
            update_data['updated_at'] = datetime.utcnow()

            # Merge metadata
            if metadata_updates:
                existing_metadata = update_data.get('metadata', {})
                merged_metadata = {**existing_metadata, **metadata_updates}
                update_data['metadata'] = merged_metadata

            # Create updated entity
            updated_entity = Entity(**update_data)

            # Update cache
            self._entity_cache[uuid] = updated_entity

            # TODO: Call Graphiti API to update entity

            logger.info(f"Entity {uuid} updated successfully")
            return updated_entity

        except Exception as e:
            logger.error(f"Failed to update entity {uuid}: {e}")
            return None

    async def delete_entity(self, uuid: str) -> bool:
        """Delete an entity.

        Args:
            uuid: Entity UUID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"Deleting entity: {uuid}")

            # Check if entity exists
            entity = await self.get_entity(uuid)
            if not entity:
                logger.warning(f"Cannot delete non-existent entity: {uuid}")
                return False

            # Remove from cache
            if uuid in self._entity_cache:
                del self._entity_cache[uuid]

            # TODO: Call Graphiti API to delete entity

            logger.info(f"Entity {uuid} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete entity {uuid}: {e}")
            return False

    async def find_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Find all entities of a specific type.

        Args:
            entity_type: Entity type to filter by

        Returns:
            List of entities matching the type
        """
        try:
            logger.info(f"Finding entities by type: {entity_type}")

            # TODO: Query Graphiti for entities by type
            # For now, search cache
            entities = [
                entity for entity in self._entity_cache.values()
                if entity.entity_type == entity_type
            ]

            logger.info(f"Found {len(entities)} entities of type {entity_type}")
            return entities

        except Exception as e:
            logger.error(f"Failed to find entities by type {entity_type}: {e}")
            return []

    async def find_entities_by_name(
        self,
        name: str,
        fuzzy: bool = False
    ) -> List[Entity]:
        """Find entities by name.

        Args:
            name: Entity name to search for
            fuzzy: If True, perform fuzzy matching (default: exact match)

        Returns:
            List of entities matching the name
        """
        try:
            logger.info(f"Finding entities by name: {name} (fuzzy={fuzzy})")

            # TODO: Implement fuzzy matching with embeddings if fuzzy=True
            # For now, do exact matching in cache
            if fuzzy:
                # Simple substring match for fuzzy
                entities = [
                    entity for entity in self._entity_cache.values()
                    if name.lower() in entity.name.lower()
                ]
            else:
                # Exact match
                entities = [
                    entity for entity in self._entity_cache.values()
                    if entity.name.lower() == name.lower()
                ]

            logger.info(f"Found {len(entities)} entities matching name {name}")
            return entities

        except Exception as e:
            logger.error(f"Failed to find entities by name {name}: {e}")
            return []

    async def search_entities(
        self,
        query: str,
        limit: int = 10
    ) -> List[Entity]:
        """Search for entities by query text.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching entities, ordered by relevance
        """
        try:
            logger.info(f"Searching entities with query: {query} (limit={limit})")

            # TODO: Use Graphiti search or embedding similarity
            # For now, simple substring search in cache
            query_lower = query.lower()
            entities = [
                entity for entity in self._entity_cache.values()
                if query_lower in entity.name.lower() or
                   query_lower in (entity.description or "").lower()
            ][:limit]

            logger.info(f"Found {len(entities)} entities matching query")
            return entities

        except Exception as e:
            logger.error(f"Failed to search entities with query {query}: {e}")
            return []

    async def batch_create_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Entity]:
        """Create multiple entities in batch.

        Args:
            entities: List of entity dictionaries with keys:
                     name, entity_type, description (optional), metadata (optional)

        Returns:
            List of created Entity objects
        """
        try:
            logger.info(f"Batch creating {len(entities)} entities")

            created_entities = []
            for entity_data in entities:
                entity = await self.create_entity(
                    name=entity_data['name'],
                    entity_type=entity_data['entity_type'],
                    description=entity_data.get('description', ''),
                    **entity_data.get('metadata', {})
                )
                created_entities.append(entity)

            logger.info(f"Successfully created {len(created_entities)} entities")
            return created_entities

        except Exception as e:
            logger.error(f"Failed to batch create entities: {e}")
            raise

    def clear_cache(self):
        """Clear the entity cache.

        This should be called when the underlying graph data changes
        to ensure cache consistency.
        """
        self._entity_cache.clear()
        logger.info("Entity cache cleared")
