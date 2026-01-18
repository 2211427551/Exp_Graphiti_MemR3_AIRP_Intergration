"""Integration tests for parser services."""

import pytest
from app.services.parser.format_detector import FormatDetector
from app.services.parser.content_classifier import ContentClassifier
from app.services.parser.world_info_parser import WorldInfoParser


@pytest.mark.asyncio
async def test_full_parsing_pipeline():
    """Test complete parsing pipeline."""
    # Initialize services
    detector = FormatDetector()
    classifier = ContentClassifier()
    world_parser = WorldInfoParser()

    # Sample input with mixed content
    input_text = """
    <核心指导>
    必须保持角色一致性。
    </核心指导>

    地点("天际省")["天际省是泰姆瑞尔帝国北部的一个省份"]

    user: 告诉我关于天际省的信息
    assistant: 天际省位于泰姆瑞尔帝国的北部，首府是独孤城。
    """

    # Step 1: Detect format
    detection_result = detector.detect_format_type(input_text)

    assert detection_result.has_world_info is True
    assert detection_result.has_chat_history is True

    # Step 2: Classify content
    classification_result = classifier.classify_content(
        detection_result.parsed_blocks,
        role_names=detection_result.role_names,
        has_world_info=detection_result.has_world_info,
        has_dialog_history=detection_result.has_chat_history
    )

    # When primary format is INSTRUCTION, only instructional blocks are extracted
    assert len(classification_result.instructional_blocks) > 0

    # Step 3: Parse world info
    world_entries = await world_parser.parse_world_info(input_text)

    assert len(world_entries) >= 1
    assert world_entries[0].name == "天际省"

    # Step 4: Parse dialog history
    dialog_turns = world_parser.parse_dialog_history(input_text)

    assert len(dialog_turns) == 2


@pytest.mark.asyncio
async def test_parse_complex_sillytavern_format():
    """Test parsing complex SillyTavern format."""
    detector = FormatDetector()

    input_text = """
    Character_Profile_of:
    名字: Alice
    职业: 冒险者

    <创作准则>
    写作风格应简洁明快
    </创作准则>

    地点("雪漫城")["天际省的主要城市之一"]
    派系("战友团")["雪漫城的战士工会"]

    user: 你是谁？
    assistant: 我是Alice，一名冒险者。
    """

    result = detector.detect_format_type(input_text)

    # Should detect multiple format indicators
    assert result.has_world_info is True
    assert result.has_chat_history is True


@pytest.mark.asyncio
async def test_concurrent_parsing_performance():
    """Test concurrent parsing performance."""
    import time

    detector = FormatDetector()
    parser = WorldInfoParser()

    # Generate large content
    world_info_entries = [
        f'地点("地点{i}")["这是地点{i}的描述"]'
        for i in range(100)
    ]

    content = '\n'.join(world_info_entries)

    # Measure parsing time
    start_time = time.time()
    entries = await parser.batch_parse(world_info_entries)
    parse_time = time.time() - start_time

    assert len(entries) == 100
    # Should complete in reasonable time (< 5 seconds for 100 entries)
    assert parse_time < 5.0
