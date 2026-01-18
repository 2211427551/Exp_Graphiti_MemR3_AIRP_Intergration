"""Format detector for SillyTavern content formats."""

import re
from typing import Optional, Tuple, List, Dict, Any

import structlog

from app.models.parsing import FormatType, ParsedBlock, DetectionResult
from app.core.config import settings
from app.core.exceptions import ParsingError

logger = structlog.get_logger(__name__)


class FormatDetector:
    """
    Detects SillyTavern content formats and extracts structured information.

    Supports detection of:
    - TEXT: Plain text content
    - INSTRUCTION: Instructional tags (<核心指导>, <禁词表>, etc.)
    - DIALOG_HISTORY: Chat conversations with role markers
    - WORLD_INFO: World book entries (地点, 类别, 派系, etc.)
    - CHARACTER_INFO: Character profile definitions
    - NARRATIVE: Narrative/story content
    """

    # Instruction tag patterns (Chinese and English)
    INSTRUCTION_TAGS = [
        r'<核心指导>.*?</核心指导>',
        r'<禁词表>.*?</禁词表>',
        r'<创作准则>.*?</创作准则>',
        r'<写作风格>.*?</写作风格>',
        r'<Core Guidance>.*?</Core Guidance>',
        r'<Forbidden Words>.*?</Forbidden Words>',
        r'<Creation Guidelines>.*?</Creation Guidelines>',
        r'<Writing Style>.*?</Writing Style>',
    ]

    # World info patterns (8 types)
    WORLD_INFO_PATTERNS = {
        'location': r'地点\("([^"]+)"\)\["(.*?)"\]',
        'category': r'类别\("([^"]+)"\)\["(.*?)"\]',
        'faction': r'派系\("([^"]+)"\)\["(.*?)"\]',
        'school': r'学校\("([^"]+)"\)\["(.*?)"\]',
        'organization': r'组织\("([^"]+)"\)\["(.*?)"\]',
        'application': r'应用\("([^"]+)"\)\["(.*?)"\]',
        'concept': r'概念\("([^"]+)"\)\["(.*?)"\]',
        'character': r'角色\("([^"]+)"\)\["(.*?)"\]',
    }

    # Dialog history patterns
    DIALOG_PATTERNS = [
        r'(user|assistant|system):\s*',  # More flexible: colon followed by optional whitespace
        r'(User|Assistant|System):\s*',
        r'<\|(user|assistant|system)\|>',
    ]

    # Character info patterns
    CHARACTER_INFO_PATTERNS = [
        r'Character_Profile_of:\s*\n',
        r'角色档案:\s*\n',
        r'<character_info>.*?</character_info>',
    ]

    def __init__(
        self,
        min_confidence: Optional[float] = None,
        strict_mode: Optional[bool] = None,
        enable_caching: Optional[bool] = None
    ):
        """
        Initialize format detector.

        Args:
            min_confidence: Minimum confidence threshold (uses settings if not provided)
            strict_mode: Enable strict pattern matching (uses settings if not provided)
            enable_caching: Cache compiled patterns (uses settings if not provided)
        """
        self.min_confidence = min_confidence or settings.parser_min_confidence
        self.strict_mode = strict_mode or settings.format_detector_strict_mode
        self.enable_caching = enable_caching or settings.parser_enable_caching

        # Compile patterns if caching is enabled
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        if self.enable_caching:
            self._compile_patterns()

        logger.info(
            "FormatDetector initialized",
            extra={
                "min_confidence": self.min_confidence,
                "strict_mode": self.strict_mode,
                "enable_caching": self.enable_caching,
            }
        )

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        # Compile instruction tags
        for i, tag in enumerate(self.INSTRUCTION_TAGS):
            self._compiled_patterns[f"instruction_{i}"] = re.compile(tag, re.DOTALL)

        # Compile world info patterns
        for entry_type, pattern in self.WORLD_INFO_PATTERNS.items():
            self._compiled_patterns[f"world_info_{entry_type}"] = re.compile(pattern)

        # Compile dialog patterns
        for i, pattern in enumerate(self.DIALOG_PATTERNS):
            self._compiled_patterns[f"dialog_{i}"] = re.compile(pattern, re.MULTILINE | re.IGNORECASE)

        # Compile character info patterns
        for i, pattern in enumerate(self.CHARACTER_INFO_PATTERNS):
            self._compiled_patterns[f"character_{i}"] = re.compile(pattern, re.DOTALL)

        logger.info("Regex patterns compiled successfully")

    def detect_format_type(
        self,
        input_text: str,
        num_results: int = 10
    ) -> DetectionResult:
        """
        Detect the format type of input text.

        Args:
            input_text: Input text to analyze
            num_results: Maximum number of parsed blocks to return

        Returns:
            DetectionResult with format type, confidence, and parsed blocks

        Raises:
            ParsingError: If detection fails
        """
        if not input_text or not input_text.strip():
            raise ParsingError("Input text is empty")

        try:
            logger.info(
                "Detecting format type",
                extra={"text_length": len(input_text)}
            )

            # Check for instruction tags
            instruction_blocks = self._extract_instruction_blocks(input_text)
            if instruction_blocks:
                return DetectionResult(
                    primary_format=FormatType.INSTRUCTION,
                    confidence=0.95,
                    parsed_blocks=instruction_blocks[:num_results],
                    has_world_info=self.has_world_info(input_text),
                    has_chat_history=self.has_chat_history(input_text),
                )

            # Check for world info
            world_info_blocks = self._extract_world_info_blocks(input_text)
            if world_info_blocks:
                return DetectionResult(
                    primary_format=FormatType.WORLD_INFO,
                    confidence=0.90,
                    parsed_blocks=world_info_blocks[:num_results],
                    has_world_info=True,
                    has_chat_history=False,
                )

            # Check for dialog history
            if self.has_chat_history(input_text):
                role_names = self.extract_role_names(input_text)
                dialog_blocks = self._extract_dialog_blocks(input_text)
                return DetectionResult(
                    primary_format=FormatType.DIALOG_HISTORY,
                    confidence=0.85,
                    parsed_blocks=dialog_blocks[:num_results],
                    role_names=role_names,
                    has_world_info=False,
                    has_chat_history=True,
                )

            # Check for character info
            if self._has_character_info(input_text):
                character_blocks = self._extract_character_blocks(input_text)
                return DetectionResult(
                    primary_format=FormatType.CHARACTER_INFO,
                    confidence=0.85,
                    parsed_blocks=character_blocks[:num_results],
                    has_world_info=False,
                    has_chat_history=False,
                )

            # Default to TEXT or NARRATIVE based on content analysis
            is_narrative = self._is_narrative_content(input_text)
            format_type = FormatType.NARRATIVE if is_narrative else FormatType.TEXT

            return DetectionResult(
                primary_format=format_type,
                confidence=0.70,
                parsed_blocks=[ParsedBlock(
                    content=input_text,
                    format_type=format_type,
                    start_pos=0,
                    end_pos=len(input_text)
                )],
                has_world_info=False,
                has_chat_history=False,
            )

        except Exception as e:
            logger.error("Format detection failed", extra={"error": str(e)})
            raise ParsingError(f"Failed to detect format: {str(e)}", content_preview=input_text[:100])

    def extract_role_names(self, input_text: str) -> Optional[Tuple[str, str]]:
        """
        Extract role names from dialog history.

        Args:
            input_text: Input text containing dialog

        Returns:
            Tuple of (user_role, assistant_role) or None
        """
        # Try to extract role names from dialog patterns
        for pattern in self.DIALOG_PATTERNS:
            matches = re.finditer(pattern, input_text, re.MULTILINE)
            roles_found = set()

            for match in matches:
                role = match.group(1).lower()
                roles_found.add(role)

                if len(roles_found) >= 2:
                    # Determine user and assistant role names
                    roles_list = sorted(roles_found)
                    return (roles_list[0], roles_list[1])

        # Default to standard roles
        return ("user", "assistant")

    def has_chat_history(self, input_text: str) -> bool:
        """
        Check if input contains chat history.

        Args:
            input_text: Input text to check

        Returns:
            True if chat history detected
        """
        for pattern in self.DIALOG_PATTERNS:
            if self.enable_caching and f"dialog_{self.DIALOG_PATTERNS.index(pattern)}" in self._compiled_patterns:
                compiled = self._compiled_patterns[f"dialog_{self.DIALOG_PATTERNS.index(pattern)}"]
            else:
                compiled = re.compile(pattern, re.MULTILINE)

            if compiled.search(input_text):
                return True

        return False

    def has_world_info(self, input_text: str) -> bool:
        """
        Check if input contains world info entries.

        Args:
            input_text: Input text to check

        Returns:
            True if world info detected
        """
        for entry_type, pattern in self.WORLD_INFO_PATTERNS.items():
            if self.enable_caching and f"world_info_{entry_type}" in self._compiled_patterns:
                compiled = self._compiled_patterns[f"world_info_{entry_type}"]
            else:
                compiled = re.compile(pattern)

            if compiled.search(input_text):
                return True

        return False

    def _extract_instruction_blocks(self, input_text: str) -> List[ParsedBlock]:
        """Extract instruction blocks from input text."""
        blocks = []

        for i, tag in enumerate(self.INSTRUCTION_TAGS):
            if self.enable_caching and f"instruction_{i}" in self._compiled_patterns:
                compiled = self._compiled_patterns[f"instruction_{i}"]
            else:
                compiled = re.compile(tag, re.DOTALL)

            for match in compiled.finditer(input_text):
                blocks.append(ParsedBlock(
                    content=match.group(0),
                    format_type=FormatType.INSTRUCTION,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"tag_type": tag.split('>')[0].split('<')[-1]}
                ))

        return sorted(blocks, key=lambda b: b.start_pos)

    def _extract_world_info_blocks(self, input_text: str) -> List[ParsedBlock]:
        """Extract world info blocks from input text."""
        blocks = []

        for entry_type, pattern in self.WORLD_INFO_PATTERNS.items():
            if self.enable_caching and f"world_info_{entry_type}" in self._compiled_patterns:
                compiled = self._compiled_patterns[f"world_info_{entry_type}"]
            else:
                compiled = re.compile(pattern)

            for match in compiled.finditer(input_text):
                blocks.append(ParsedBlock(
                    content=match.group(0),
                    format_type=FormatType.WORLD_INFO,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={
                        "entry_type": entry_type,
                        "name": match.group(1),
                        "description": match.group(2)
                    },
                    extracted_entities=[match.group(1)]
                ))

        return sorted(blocks, key=lambda b: b.start_pos)

    def _extract_dialog_blocks(self, input_text: str) -> List[ParsedBlock]:
        """Extract dialog blocks from input text."""
        blocks = []
        lines = input_text.split('\n')
        current_block = []
        current_start = 0
        current_role = None

        for i, line in enumerate(lines):
            # Check if line starts with role marker
            for pattern in self.DIALOG_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    # Save previous block if exists
                    if current_block and current_role:
                        blocks.append(ParsedBlock(
                            content='\n'.join(current_block),
                            format_type=FormatType.DIALOG_HISTORY,
                            start_pos=current_start,
                            end_pos=current_start + len('\n'.join(current_block)),
                            metadata={"role": current_role}
                        ))

                    # Start new block
                    current_role = match.group(1).lower()
                    current_block = [line]
                    current_start = sum(len(l) + 1 for l in lines[:i])
                    break
            else:
                if current_block:
                    current_block.append(line)

        # Add last block
        if current_block and current_role:
            blocks.append(ParsedBlock(
                content='\n'.join(current_block),
                format_type=FormatType.DIALOG_HISTORY,
                start_pos=current_start,
                end_pos=len(input_text),
                metadata={"role": current_role}
            ))

        return blocks

    def _has_character_info(self, input_text: str) -> bool:
        """Check if input contains character info."""
        for pattern in self.CHARACTER_INFO_PATTERNS:
            if self.enable_caching and f"character_{self.CHARACTER_INFO_PATTERNS.index(pattern)}" in self._compiled_patterns:
                compiled = self._compiled_patterns[f"character_{self.CHARACTER_INFO_PATTERNS.index(pattern)}"]
            else:
                compiled = re.compile(pattern, re.DOTALL)

            if compiled.search(input_text):
                return True

        return False

    def _extract_character_blocks(self, input_text: str) -> List[ParsedBlock]:
        """Extract character info blocks from input text."""
        blocks = []

        for i, pattern in enumerate(self.CHARACTER_INFO_PATTERNS):
            if self.enable_caching and f"character_{i}" in self._compiled_patterns:
                compiled = self._compiled_patterns[f"character_{i}"]
            else:
                compiled = re.compile(pattern, re.DOTALL)

            for match in compiled.finditer(input_text):
                blocks.append(ParsedBlock(
                    content=match.group(0),
                    format_type=FormatType.CHARACTER_INFO,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))

        return blocks

    def _is_narrative_content(self, input_text: str) -> bool:
        """
        Determine if content is narrative (story-like) vs plain text.

        Args:
            input_text: Input text to analyze

        Returns:
            True if content appears to be narrative
        """
        # Narrative indicators
        narrative_indicators = [
            r'\b说\b', r'\b想\b', r'\b看\b',  # Chinese dialogue markers
            r'\bsaid\b', r'\bthought\b', r'\bsaw\b',  # English dialogue markers
            r'"[^"]*"',  # Quoted speech
            r'。.*?，',  # Chinese narrative flow
        ]

        match_count = 0
        for indicator in narrative_indicators:
            if re.search(indicator, input_text):
                match_count += 1

        # Consider narrative if multiple indicators found
        return match_count >= 2
