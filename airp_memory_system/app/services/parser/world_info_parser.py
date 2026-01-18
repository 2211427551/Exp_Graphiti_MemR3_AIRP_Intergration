"""World info parser for extracting structured world book entries."""

import re
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog

from app.models.parsing import WorldInfoEntry, WorldInfoType, DialogTurn
from app.core.config import settings
from app.core.exceptions import ParsingError
from app.services.hash_computation import HashComputationService

logger = structlog.get_logger(__name__)


class WorldInfoParser:
    """
    Parses world info entries from SillyTavern world book format.

    Supports 8 world info entry types:
    - location: 地点("name")["description"]
    - category: 类别("name")["description"]
    - faction: 派系("name")["description"]
    - school: 学校("name")["description"]
    - organization: 组织("name")["description"]
    - application: 应用("name")["description"]
    - concept: 概念("name")["description"]
    - character: 角色("name")["description"]
    """

    # Compiled regex patterns for each entry type
    PATTERNS = {
        WorldInfoType.LOCATION: re.compile(r'地点\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.CATEGORY: re.compile(r'类别\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.FACTION: re.compile(r'派系\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.SCHOOL: re.compile(r'学校\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.ORGANIZATION: re.compile(r'组织\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.APPLICATION: re.compile(r'应用\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.CONCEPT: re.compile(r'概念\("([^"]+)"\)\["(.*?)"\]'),
        WorldInfoType.CHARACTER: re.compile(r'角色\("([^"]+)"\)\["(.*?)"\]'),
    }

    def __init__(
        self,
        compute_hashes: Optional[bool] = None,
        max_entry_length: Optional[int] = None,
        max_workers: Optional[int] = None,
        hash_service: Optional[HashComputationService] = None
    ):
        """
        Initialize world info parser.

        Args:
            compute_hashes: Compute MD5 hashes for entries (uses settings if not provided)
            max_entry_length: Maximum entry length (uses settings if not provided)
            max_workers: Max workers for concurrent parsing (uses settings if not provided)
            hash_service: Hash computation service (creates new if not provided)
        """
        self.compute_hashes = compute_hashes or settings.world_info_parser_compute_hashes
        self.max_entry_length = max_entry_length or settings.world_info_parser_max_entry_length
        self.max_workers = max_workers or settings.parser_max_workers
        self.hash_service = hash_service or HashComputationService()

        logger.info(
            "WorldInfoParser initialized",
            extra={
                "compute_hashes": self.compute_hashes,
                "max_entry_length": self.max_entry_length,
                "max_workers": self.max_workers,
            }
        )

    async def parse_world_info(
        self,
        content: str,
        source: str = "unknown"
    ) -> List[WorldInfoEntry]:
        """
        Parse world info entries from content.

        Args:
            content: Content containing world info entries
            source: Source identifier for metadata

        Returns:
            List of parsed WorldInfoEntry objects

        Raises:
            ParsingError: If parsing fails
        """
        if not content or not content.strip():
            return []

        try:
            logger.info(
                "Parsing world info",
                extra={
                    "content_length": len(content),
                    "source": source,
                }
            )

            entries = []

            # Parse each entry type
            for entry_type, pattern in self.PATTERNS.items():
                matches = pattern.finditer(content)

                for match in matches:
                    entry = self.parse_entry(
                        match.group(0),
                        entry_type,
                        source
                    )

                    if entry:
                        entries.append(entry)

            logger.info(
                "World info parsed successfully",
                extra={
                    "total_entries": len(entries),
                    "entry_types": {entry_type.value: len([x for x in entries if x.entry_type == entry_type]) for entry_type in WorldInfoType},
                }
            )

            return entries

        except Exception as e:
            logger.error("World info parsing failed", extra={"error": str(e)})
            raise ParsingError(
                f"Failed to parse world info: {str(e)}",
                content_preview=content[:100]
            )

    def parse_entry(
        self,
        entry_text: str,
        entry_type: WorldInfoType,
        source: str = "unknown"
    ) -> Optional[WorldInfoEntry]:
        """
        Parse a single world info entry.

        Args:
            entry_text: Entry text to parse
            entry_type: Type of world info entry
            source: Source identifier for metadata

        Returns:
            WorldInfoEntry or None if parsing fails
        """
        try:
            # Get pattern for entry type
            pattern = self.PATTERNS.get(entry_type)
            if not pattern:
                logger.warning("Unknown entry type", extra={"entry_type": entry_type})
                return None

            # Extract name and content
            match = pattern.search(entry_text)
            if not match:
                return None

            name = match.group(1)
            content = match.group(2)

            # Truncate if too long
            if len(content) > self.max_entry_length:
                content = content[:self.max_entry_length]
                logger.warning(
                    "Entry content truncated",
                    extra={
                        "name": name,
                        "original_length": len(match.group(2)),
                        "truncated_length": self.max_entry_length,
                    }
                )

            # Compute hash if enabled
            entry_hash = None
            if self.compute_hashes:
                entry_hash = self.hash_service.compute_world_info_hash(
                    entry_type, name, content
                )

            return WorldInfoEntry(
                entry_type=entry_type,
                name=name,
                content=content,
                hash=entry_hash,
                metadata={
                    "source": source,
                    "original_text": entry_text,
                    "content_length": len(content),
                }
            )

        except Exception as e:
            logger.error("Failed to parse entry", extra={"error": str(e), "entry_text": entry_text[:100]})
            return None

    async def batch_parse(
        self,
        entries: List[str],
        source: str = "batch"
    ) -> List[WorldInfoEntry]:
        """
        Parse multiple world info entries concurrently.

        Args:
            entries: List of entry texts to parse
            source: Source identifier for metadata

        Returns:
            List of parsed WorldInfoEntry objects
        """
        if not entries:
            return []

        logger.info(
            "Batch parsing world info entries",
            extra={
                "total_entries": len(entries),
                "max_workers": self.max_workers,
            }
        )

        all_entries = []

        # Use ThreadPoolExecutor for concurrent parsing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all parsing tasks
            future_to_entry = {}

            for entry_text in entries:
                # Determine entry type from text
                entry_type = self._detect_entry_type(entry_text)
                if entry_type:
                    future = executor.submit(self.parse_entry, entry_text, entry_type, source)
                    future_to_entry[future] = entry_text

            # Collect results as they complete
            for future in as_completed(future_to_entry):
                entry = future.result()
                if entry:
                    all_entries.append(entry)

        logger.info(
            "Batch parsing completed",
            extra={
                "successful_parses": len(all_entries),
                "total_entries": len(entries),
            }
        )

        return all_entries

    def _detect_entry_type(self, entry_text: str) -> Optional[WorldInfoType]:
        """
        Detect the type of world info entry from text.

        Args:
            entry_text: Entry text to analyze

        Returns:
            Detected WorldInfoType or None
        """
        for entry_type, pattern in self.PATTERNS.items():
            if pattern.search(entry_text):
                return entry_type

        return None

    def parse_dialog_history(self, content: str) -> List[DialogTurn]:
        """
        Parse dialog history from content.

        Args:
            content: Content containing dialog history

        Returns:
            List of DialogTurn objects
        """
        turns = []
        lines = content.split('\n')
        turn_number = 0

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Check for role marker with content (case-insensitive, allow leading whitespace)
            role_match = re.match(r'^\s*(user|assistant|system):\s*(.+)$', line, flags=re.IGNORECASE)
            if role_match:
                role = role_match.group(1).lower()
                message = role_match.group(2).strip()

                if message:  # Only create turn if there's actual content
                    # Compute hash if enabled
                    turn_hash = None
                    if self.compute_hashes:
                        turn_hash = self.hash_service.compute_dialog_turn_hash(
                            role, message, turn_number
                        )

                    turns.append(DialogTurn(
                        role=role,
                        content=message,
                        turn_number=turn_number,
                        hash=turn_hash
                    ))
                    turn_number += 1

        logger.info(
            "Dialog history parsed",
            extra={"total_turns": len(turns)}
        )

        return turns
