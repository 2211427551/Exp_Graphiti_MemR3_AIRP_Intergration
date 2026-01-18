"""Content classifier for categorizing parsed content blocks."""

from typing import List, Tuple, Optional

import structlog

from app.models.parsing import ParsedBlock, ClassifiedContent, FormatType
from app.core.config import settings
from app.core.exceptions import ClassificationError

logger = structlog.get_logger(__name__)


class ContentClassifier:
    """
    Classifies content as instructional or narrative.

    Classification rules:
    - INSTRUCTIONAL: Contains guidance, rules, constraints, instructions
    - NARRATIVE: Story content, dialogue, descriptions
    - MIXED: Combination of both types
    """

    # Instructional tag markers
    INSTRUCTIONAL_TAGS = {
        '<核心指导>', '</核心指导>',
        '<禁词表>', '</禁词表>',
        '<创作准则>', '</创作准则>',
        '<写作风格>', '</写作风格>',
        '<Core Guidance>', '</Core Guidance>',
        '<Forbidden Words>', '</Forbidden Words>',
        '<Creation Guidelines>', '</Creation Guidelines>',
        '<Writing Style>', '</Writing Style>',
    }

    # Instructional keywords
    INSTRUCTIONAL_KEYWORDS = [
        'must', 'should', 'must not', 'forbidden',
        '必须', '禁止', '应该', '不要',
        'requirement', 'constraint', 'rule',
        '要求', '约束', '规则',
    ]

    # Narrative keywords
    NARRATIVE_KEYWORDS = [
        'Character_Profile_of:',
        '地点("', '类别("', '派系("',
        'said', 'replied', 'asked', 'thought',
        '说', '想', '问', '回答',
    ]

    def __init__(
        self,
        threshold: Optional[float] = None,
        min_block_size: Optional[int] = None
    ):
        """
        Initialize content classifier.

        Args:
            threshold: Classification confidence threshold (uses settings if not provided)
            min_block_size: Minimum block size to classify (uses settings if not provided)
        """
        self.threshold = threshold or settings.content_classifier_threshold
        self.min_block_size = min_block_size or settings.content_classifier_min_block_size

        logger.info(
            "ContentClassifier initialized",
            extra={
                "threshold": self.threshold,
                "min_block_size": self.min_block_size,
            }
        )

    def classify_content(
        self,
        parsed_blocks: List[ParsedBlock],
        role_names: Optional[Tuple[str, str]] = None,
        has_world_info: bool = False,
        has_dialog_history: bool = False
    ) -> ClassifiedContent:
        """
        Classify content blocks into instructional and narrative categories.

        Args:
            parsed_blocks: List of parsed blocks to classify
            role_names: Role names if dialog history present
            has_world_info: Whether world info is present
            has_dialog_history: Whether dialog history is present

        Returns:
            ClassifiedContent with separated blocks and confidence score

        Raises:
            ClassificationError: If classification fails
        """
        if not parsed_blocks:
            raise ClassificationError("No content blocks to classify")

        try:
            logger.info(
                "Classifying content",
                extra={
                    "num_blocks": len(parsed_blocks),
                    "has_world_info": has_world_info,
                    "has_dialog_history": has_dialog_history,
                }
            )

            instructional_blocks = []
            narrative_blocks = []
            confidence_scores = []

            for block in parsed_blocks:
                # Skip blocks smaller than minimum size
                if len(block.content.strip()) < self.min_block_size:
                    continue

                if self.is_instructional(block):
                    instructional_blocks.append(block)
                    confidence_scores.append(self._instructional_confidence(block))
                elif self.is_narrative(block):
                    narrative_blocks.append(block)
                    confidence_scores.append(self._narrative_confidence(block))
                else:
                    # Default to narrative for uncertain blocks
                    narrative_blocks.append(block)
                    confidence_scores.append(0.5)

            # Calculate overall confidence
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5

            result = ClassifiedContent(
                instructional_blocks=instructional_blocks,
                narrative_blocks=narrative_blocks,
                role_names=role_names,
                has_world_info=has_world_info,
                has_dialog_history=has_dialog_history,
                confidence_score=overall_confidence
            )

            logger.info(
                "Content classified successfully",
                extra={
                    "instructional_blocks": len(instructional_blocks),
                    "narrative_blocks": len(narrative_blocks),
                    "confidence": overall_confidence,
                }
            )

            return result

        except Exception as e:
            logger.error("Content classification failed", extra={"error": str(e)})
            raise ClassificationError(
                f"Failed to classify content: {str(e)}",
                confidence_score=0.0
            )

    def is_instructional(self, block: ParsedBlock) -> bool:
        """
        Check if a block is instructional content.

        Args:
            block: ParsedBlock to check

        Returns:
            True if block appears instructional
        """
        # Check format type
        if block.format_type == FormatType.INSTRUCTION:
            return True

        content_lower = block.content.lower()

        # Check for instructional tags
        for tag in self.INSTRUCTIONAL_TAGS:
            if tag.lower() in content_lower:
                return True

        # Check for instructional keywords
        instructional_count = sum(
            1 for keyword in self.INSTRUCTIONAL_KEYWORDS
            if keyword.lower() in content_lower
        )

        # Consider instructional if multiple keywords found
        return instructional_count >= 2

    def is_narrative(self, block: ParsedBlock) -> bool:
        """
        Check if a block is narrative content.

        Args:
            block: ParsedBlock to check

        Returns:
            True if block appears narrative
        """
        # Check format type
        if block.format_type in [FormatType.NARRATIVE, FormatType.DIALOG_HISTORY, FormatType.CHARACTER_INFO]:
            return True

        # World info is narrative content
        if block.format_type == FormatType.WORLD_INFO:
            return True

        content_lower = block.content.lower()

        # Check for narrative keywords
        narrative_count = sum(
            1 for keyword in self.NARRATIVE_KEYWORDS
            if keyword.lower() in content_lower
        )

        # Consider narrative if multiple keywords found
        return narrative_count >= 1

    def _instructional_confidence(self, block: ParsedBlock) -> float:
        """Calculate confidence score for instructional classification."""
        if block.format_type == FormatType.INSTRUCTION:
            return 0.95

        content_lower = block.content.lower()
        score = 0.5  # Base score

        # Increase score for each instructional tag found
        for tag in self.INSTRUCTIONAL_TAGS:
            if tag.lower() in content_lower:
                score += 0.15

        # Increase score for each instructional keyword found
        for keyword in self.INSTRUCTIONAL_KEYWORDS:
            if keyword.lower() in content_lower:
                score += 0.05

        return min(score, 1.0)

    def _narrative_confidence(self, block: ParsedBlock) -> float:
        """Calculate confidence score for narrative classification."""
        if block.format_type in [FormatType.NARRATIVE, FormatType.DIALOG_HISTORY, FormatType.WORLD_INFO]:
            return 0.90

        content_lower = block.content.lower()
        score = 0.5  # Base score

        # Increase score for each narrative keyword found
        for keyword in self.NARRATIVE_KEYWORDS:
            if keyword.lower() in content_lower:
                score += 0.10

        return min(score, 1.0)
