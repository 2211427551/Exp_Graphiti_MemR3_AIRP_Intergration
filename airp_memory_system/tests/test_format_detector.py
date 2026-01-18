"""Unit tests for FormatDetector service."""

import pytest
from app.services.parser.format_detector import FormatDetector
from app.models.parsing import FormatType


@pytest.mark.asyncio
async def test_detect_instruction_format():
    """Test detection of instructional content."""
    detector = FormatDetector()

    input_text = """
    <核心指导>
    这是一个核心指导内容。
    必须遵守这些规则。
    </核心指导>
    """

    result = detector.detect_format_type(input_text)

    assert result.primary_format == FormatType.INSTRUCTION
    assert result.confidence >= 0.9
    assert len(result.parsed_blocks) > 0


@pytest.mark.asyncio
async def test_detect_world_info_format():
    """Test detection of world info content."""
    detector = FormatDetector()

    input_text = """
    地点("天际省")["天际省是泰姆瑞尔帝国北部的一个省份"]
    类别("城市")["城市是人类聚居地"]
    """

    result = detector.detect_format_type(input_text)

    assert result.primary_format == FormatType.WORLD_INFO
    assert result.has_world_info is True
    assert len(result.parsed_blocks) >= 2


@pytest.mark.asyncio
async def test_detect_dialog_history():
    """Test detection of dialog history."""
    detector = FormatDetector()

    input_text = """
    user: 你好
    assistant: 你好！有什么我可以帮助你的吗？
    user: 告诉我关于天际省的信息
    """

    result = detector.detect_format_type(input_text)

    assert result.primary_format == FormatType.DIALOG_HISTORY
    assert result.has_chat_history is True
    assert result.role_names is not None


@pytest.mark.asyncio
async def test_detect_narrative_content():
    """Test detection of narrative content."""
    detector = FormatDetector()

    input_text = """
    Alice walked into the room and said, "Hello everyone."
    Bob looked up and replied, "Hi Alice, glad you could make it."
    """

    result = detector.detect_format_type(input_text)

    assert result.primary_format in [FormatType.NARRATIVE, FormatType.TEXT]


@pytest.mark.asyncio
async def test_extract_role_names():
    """Test extraction of role names from dialog."""
    detector = FormatDetector()

    input_text = """
    user: Question here
    assistant: Answer here
    """

    role_names = detector.extract_role_names(input_text)

    assert role_names is not None
    assert len(role_names) == 2


@pytest.mark.asyncio
async def test_has_world_info():
    """Test world info detection."""
    detector = FormatDetector()

    input_text = '地点("测试")["description"]'
    assert detector.has_world_info(input_text) is True

    input_text = "Plain text without world info"
    assert detector.has_world_info(input_text) is False
