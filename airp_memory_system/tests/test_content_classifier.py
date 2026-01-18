"""Unit tests for ContentClassifier service."""

import pytest
from app.services.parser.content_classifier import ContentClassifier
from app.models.parsing import ParsedBlock, FormatType


@pytest.mark.asyncio
async def test_classify_instructional_content():
    """Test classification of instructional content."""
    classifier = ContentClassifier()

    blocks = [
        ParsedBlock(
            content="<核心指导>必须遵守的规则</核心指导>",
            format_type=FormatType.INSTRUCTION,
            start_pos=0,
            end_pos=20
        )
    ]

    result = classifier.classify_content(blocks)

    assert len(result.instructional_blocks) > 0
    assert result.confidence_score >= 0.6


@pytest.mark.asyncio
async def test_classify_narrative_content():
    """Test classification of narrative content."""
    classifier = ContentClassifier()

    blocks = [
        ParsedBlock(
            content='Alice said, "Hello world."',
            format_type=FormatType.NARRATIVE,
            start_pos=0,
            end_pos=26
        )
    ]

    result = classifier.classify_content(blocks)

    assert len(result.narrative_blocks) > 0


@pytest.mark.asyncio
async def test_is_instructional():
    """Test instructional content detection."""
    classifier = ContentClassifier()

    block = ParsedBlock(
        content="<核心指导>规则内容</核心指导>",
        format_type=FormatType.INSTRUCTION,
        start_pos=0,
        end_pos=20
    )

    assert classifier.is_instructional(block) is True


@pytest.mark.asyncio
async def test_is_narrative():
    """Test narrative content detection."""
    classifier = ContentClassifier()

    block = ParsedBlock(
        content="Alice said something",
        format_type=FormatType.NARRATIVE,
        start_pos=0,
        end_pos=20
    )

    assert classifier.is_narrative(block) is True
