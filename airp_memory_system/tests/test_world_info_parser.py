"""Unit tests for WorldInfoParser service."""

import pytest
from app.services.parser.world_info_parser import WorldInfoParser
from app.models.parsing import WorldInfoType


@pytest.mark.asyncio
async def test_parse_location_entry():
    """Test parsing location world info entry."""
    parser = WorldInfoParser()

    content = '地点("天际省")["天际省是泰姆瑞尔帝国的北部省份"]'

    entries = await parser.parse_world_info(content)

    assert len(entries) == 1
    assert entries[0].entry_type == WorldInfoType.LOCATION
    assert entries[0].name == "天际省"
    assert "天际省是泰姆瑞尔帝国" in entries[0].content


@pytest.mark.asyncio
async def test_parse_multiple_entry_types():
    """Test parsing multiple world info entry types."""
    parser = WorldInfoParser()

    content = """
    地点("天际省")["省份描述"]
    类别("城市")["城市类型"]
    派系("黑暗兄弟会")["刺客组织"]
    """

    entries = await parser.parse_world_info(content)

    assert len(entries) == 3
    entry_types = {e.entry_type for e in entries}
    assert WorldInfoType.LOCATION in entry_types
    assert WorldInfoType.CATEGORY in entry_types
    assert WorldInfoType.FACTION in entry_types


@pytest.mark.asyncio
async def test_parse_with_hash_computation():
    """Test hash computation for entries."""
    parser = WorldInfoParser(compute_hashes=True)

    content = '地点("测试")["测试内容"]'

    entries = await parser.parse_world_info(content)

    assert entries[0].hash is not None
    assert len(entries[0].hash) == 32  # MD5 hash length


@pytest.mark.asyncio
async def test_batch_parse():
    """Test batch parsing of entries."""
    parser = WorldInfoParser()

    entries = [
        '地点("地点1")["描述1"]',
        '类别("类别1")["描述2"]',
        '派系("派系1")["描述3"]',
    ]

    results = await parser.batch_parse(entries)

    assert len(results) == 3


def test_parse_dialog_history():
    """Test dialog history parsing."""
    parser = WorldInfoParser()

    content = """
    user: 你好
    assistant: 你好！有什么我可以帮助你的吗？
    user: 告诉我关于天际省的信息
    assistant: 天际省是泰姆瑞尔帝国北部的一个省份...
    """

    turns = parser.parse_dialog_history(content)

    assert len(turns) == 4
    assert turns[0].role == "user"
    assert turns[1].role == "assistant"
