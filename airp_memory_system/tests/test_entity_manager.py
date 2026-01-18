"""Tests for EntityManager service (Week 5)."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.services.memory.entity_manager import EntityManager
from app.models.memory import Entity
from app.services.memory.graphiti_client import GraphitiClient


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient."""
    client = Mock(spec=GraphitiClient)
    return client


@pytest.fixture
def entity_manager(mock_graphiti_client):
    """Create an EntityManager instance with mock client."""
    return EntityManager(mock_graphiti_client)


@pytest.mark.asyncio
async def test_create_entity(entity_manager):
    """Test basic entity creation."""
    entity = await entity_manager.create_entity(
        name="天际省",
        entity_type="location",
        description="天际省是泰姆瑞尔帝国的北部省份"
    )

    assert entity is not None
    assert entity.uuid is not None
    assert entity.name == "天际省"
    assert entity.entity_type == "location"
    assert "天际省是泰姆瑞尔帝国的北部省份" in entity.description
    assert entity.created_at is not None
    assert entity.updated_at is not None


@pytest.mark.asyncio
async def test_create_entity_with_metadata(entity_manager):
    """Test entity creation with metadata."""
    entity = await entity_manager.create_entity(
        name="独孤城",
        entity_type="location",
        description="天际省首府",
        capital=True,
        population=10000
    )

    assert entity is not None
    assert entity.metadata.get('capital') is True
    assert entity.metadata.get('population') == 10000


@pytest.mark.asyncio
async def test_get_entity(entity_manager):
    """Test retrieving entity by UUID."""
    # Create an entity first
    created = await entity_manager.create_entity(
        name="风盔城",
        entity_type="location",
        description="天际省东部城市"
    )

    # Get the entity
    retrieved = await entity_manager.get_entity(created.uuid)

    assert retrieved is not None
    assert retrieved.uuid == created.uuid
    assert retrieved.name == "风盔城"
    assert retrieved.entity_type == "location"


@pytest.mark.asyncio
async def test_get_nonexistent_entity(entity_manager):
    """Test retrieving non-existent entity returns None."""
    retrieved = await entity_manager.get_entity("nonexistent-uuid")
    assert retrieved is None


@pytest.mark.asyncio
async def test_update_entity(entity_manager):
    """Test updating entity metadata."""
    # Create an entity
    entity = await entity_manager.create_entity(
        name="裂谷城",
        entity_type="location",
        description="天际省南部城市"
    )

    # Update the entity
    updated = await entity_manager.update_entity(
        entity.uuid,
        description="天际省南部首府，以盗贼公会闻名",
        population=8000,
        has_thieves_guild=True
    )

    assert updated is not None
    assert updated.uuid == entity.uuid
    assert "盗贼公会" in updated.description
    assert updated.metadata.get('population') == 8000
    assert updated.metadata.get('has_thieves_guild') is True
    # Note: updated_at might be slightly different due to timing
    assert updated.updated_at >= entity.created_at


@pytest.mark.asyncio
async def test_update_nonexistent_entity(entity_manager):
    """Test updating non-existent entity returns None."""
    updated = await entity_manager.update_entity(
        "nonexistent-uuid",
        name="New Name"
    )
    assert updated is None


@pytest.mark.asyncio
async def test_delete_entity(entity_manager):
    """Test entity deletion."""
    # Create an entity
    entity = await entity_manager.create_entity(
        name="冬堡",
        entity_type="location",
        description="天际省北部城市"
    )

    # Delete the entity
    deleted = await entity_manager.delete_entity(entity.uuid)

    assert deleted is True

    # Verify entity is deleted
    retrieved = await entity_manager.get_entity(entity.uuid)
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(entity_manager):
    """Test deleting non-existent entity returns False."""
    deleted = await entity_manager.delete_entity("nonexistent-uuid")
    assert deleted is False


@pytest.mark.asyncio
async def test_find_entities_by_type(entity_manager):
    """Test filtering entities by type."""
    # Create multiple entities
    await entity_manager.create_entity("天际省", "location", "北部省份")
    await entity_manager.create_entity("独孤城", "location", "首府")
    await entity_manager.create_entity("乌尔夫", "person", "诺德人战士")
    await entity_manager.create_entity("艾莉萨", "person", "帝国法师")

    # Find locations
    locations = await entity_manager.find_entities_by_type("location")

    assert len(locations) == 2
    assert all(e.entity_type == "location" for e in locations)

    # Find people
    people = await entity_manager.find_entities_by_type("person")

    assert len(people) == 2
    assert all(e.entity_type == "person" for e in people)


@pytest.mark.asyncio
async def test_find_entities_by_name_exact(entity_manager):
    """Test finding entities by exact name match."""
    # Create entities
    await entity_manager.create_entity("天际省", "location", "北部省份")
    await entity_manager.create_entity("幽影沼泽", "location", "南部省份")

    # Find by exact name
    results = await entity_manager.find_entities_by_name("天际省", fuzzy=False)

    assert len(results) == 1
    assert results[0].name == "天际省"


@pytest.mark.asyncio
async def test_find_entities_by_name_fuzzy(entity_manager):
    """Test finding entities with fuzzy name matching."""
    # Create entities
    await entity_manager.create_entity("天际省", "location", "北部省份")
    await entity_manager.create_entity("天际帝国", "organization", "泰姆瑞尔帝国")

    # Find with fuzzy match (substring)
    results = await entity_manager.find_entities_by_name("天际", fuzzy=True)

    assert len(results) == 2
    assert all("天际" in e.name for e in results)


@pytest.mark.asyncio
async def test_search_entities(entity_manager):
    """Test searching entities by query text."""
    # Create entities
    await entity_manager.create_entity(
        "独孤城",
        "location",
        "天际省首府，位于西部的城市"
    )
    await entity_manager.create_entity(
        "风盔城",
        "location",
        "天际省东部的诺德文化城市"
    )
    await entity_manager.create_entity(
        "乌尔夫",
        "person",
        "来自天际省的诺德人战士"
    )

    # Search for "城市"
    results = await entity_manager.search_entities("城市", limit=10)

    assert len(results) >= 2
    assert all(
        "城市" in e.name or "城市" in (e.description or "")
        for e in results
    )


@pytest.mark.asyncio
async def test_search_entities_with_limit(entity_manager):
    """Test search respects limit parameter."""
    # Create multiple entities
    for i in range(5):
        await entity_manager.create_entity(
            f"地点{i}",
            "location",
            f"这是第{i}个地点"
        )

    # Search with limit
    results = await entity_manager.search_entities("地点", limit=3)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_batch_create_entities(entity_manager):
    """Test batch entity creation."""
    entities_data = [
        {
            "name": "独孤城",
            "entity_type": "location",
            "description": "天际省首府",
            "metadata": {"capital": True}
        },
        {
            "name": "风盔城",
            "entity_type": "location",
            "description": "东部城市"
        },
        {
            "name": "裂谷城",
            "entity_type": "location",
            "description": "南部城市"
        }
    ]

    created = await entity_manager.batch_create_entities(entities_data)

    assert len(created) == 3
    assert all(isinstance(e, Entity) for e in created)
    assert all(e.uuid is not None for e in created)
    assert created[0].metadata.get('capital') is True


@pytest.mark.asyncio
async def test_clear_cache(entity_manager):
    """Test clearing entity cache."""
    # Create entities
    await entity_manager.create_entity("测试地点", "location", "测试描述")

    # Clear cache
    entity_manager.clear_cache()

    # Verify cache is empty
    assert len(entity_manager._entity_cache) == 0


@pytest.mark.asyncio
async def test_entity_caching_behavior(entity_manager):
    """Test that entities are properly cached."""
    # Create an entity
    entity = await entity_manager.create_entity("测试", "location", "描述")

    # Verify it's in cache
    assert entity.uuid in entity_manager._entity_cache

    # Retrieve from cache
    retrieved = await entity_manager.get_entity(entity.uuid)

    # Verify it's the same object (cached)
    assert retrieved.uuid == entity.uuid

    # Update should update cache
    updated = await entity_manager.update_entity(entity.uuid, description="新描述")
    assert updated.description == "新描述"
    assert entity_manager._entity_cache[entity.uuid].description == "新描述"

    # Delete should remove from cache
    await entity_manager.delete_entity(entity.uuid)
    assert entity.uuid not in entity_manager._entity_cache


@pytest.mark.asyncio
async def test_update_entity_preserves_metadata(entity_manager):
    """Test that update preserves existing metadata unless explicitly changed."""
    # Create entity with metadata
    entity = await entity_manager.create_entity(
        "测试",
        "location",
        "描述",
        key1="value1",
        key2="value2"
    )

    # Update with new metadata
    updated = await entity_manager.update_entity(
        entity.uuid,
        description="新描述",
        key1="new_value1"
    )

    # Check that key1 is updated, key2 is preserved
    assert updated.metadata.get('key1') == "new_value1"
    assert updated.metadata.get('key2') == "value2"
