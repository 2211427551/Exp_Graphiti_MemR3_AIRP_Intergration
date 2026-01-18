"""Change detection service for world info and dialog history."""

import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

import structlog

from app.models.parsing import WorldInfoEntry, DialogTurn, WorldInfoType
from app.models.change_detection import (
    ChangeType,
    EntryChange,
    ChangeReport,
    DialogDiff,
    HashAlgorithm,
)
from app.services.hash_computation import HashComputationService
from app.core.config import settings
from app.core.exceptions import AIRPMemoryError

logger = structlog.get_logger(__name__)


class ChangeDetectionError(AIRPMemoryError):
    """Exception raised when change detection fails."""
    pass


class ChangeDetector:
    """
    Detects changes between versions of world info and dialog history.

    Capabilities:
    - Detect added/removed/modified world info entries
    - Detect structural changes in dialog history (turn count, role sequence)
    - Detect content changes in dialog turns
    - Generate detailed change reports
    - Batch change detection
    """

    def __init__(
        self,
        hash_service: Optional[HashComputationService] = None,
        algorithm: Optional[HashAlgorithm] = None
    ):
        """
        Initialize change detector.

        Args:
            hash_service: Hash computation service (creates new if not provided)
            algorithm: Hash algorithm to use (uses settings if not provided)
        """
        self.hash_service = hash_service or HashComputationService(algorithm=algorithm)
        self.algorithm = self.hash_service.algorithm

        logger.info(
            "ChangeDetector initialized",
            extra={"algorithm": self.algorithm.value}
        )

    # ============================================
    # World Info Change Detection
    # ============================================

    def detect_world_info_changes(
        self,
        before: List[WorldInfoEntry],
        after: List[WorldInfoEntry]
    ) -> ChangeReport:
        """
        Detect changes between two sets of world info entries.

        Args:
            before: Previous world info entries
            after: New world info entries

        Returns:
            ChangeReport with all detected changes

        Raises:
            ChangeDetectionError: If detection fails
        """
        start_time = time.time()

        try:
            logger.info(
                "Detecting world info changes",
                extra={
                    "before_count": len(before),
                    "after_count": len(after)
                }
            )

            # Build lookup dictionaries
            before_dict = self._build_world_info_lookup(before)
            after_dict = self._build_world_info_lookup(after)

            # Detect changes
            changes = []
            added_count = 0
            removed_count = 0
            modified_count = 0
            unchanged_count = 0

            # Check for added and modified entries
            for key, new_entry in after_dict.items():
                if key not in before_dict:
                    # Entry added
                    changes.append(EntryChange(
                        change_type=ChangeType.ADDED,
                        entry_type="world_info",
                        identifier=key,
                        old_hash=None,
                        new_hash=new_entry.hash,
                        old_value=None,
                        new_value=self._serialize_world_info(new_entry),
                        entry_type_field=new_entry.entry_type.value,
                        name=new_entry.name,
                    ))
                    added_count += 1
                else:
                    old_entry = before_dict[key]
                    # Check if modified (hash comparison)
                    if old_entry.hash != new_entry.hash:
                        changes.append(EntryChange(
                            change_type=ChangeType.MODIFIED,
                            entry_type="world_info",
                            identifier=key,
                            old_hash=old_entry.hash,
                            new_hash=new_entry.hash,
                            old_value=self._serialize_world_info(old_entry),
                            new_value=self._serialize_world_info(new_entry),
                            entry_type_field=new_entry.entry_type.value,
                            name=new_entry.name,
                            content=new_entry.content,
                        ))
                        modified_count += 1
                    else:
                        unchanged_count += 1

            # Check for removed entries
            for key, old_entry in before_dict.items():
                if key not in after_dict:
                    changes.append(EntryChange(
                        change_type=ChangeType.REMOVED,
                        entry_type="world_info",
                        identifier=key,
                        old_hash=old_entry.hash,
                        new_hash=None,
                        old_value=self._serialize_world_info(old_entry),
                        new_value=None,
                        entry_type_field=old_entry.entry_type.value,
                        name=old_entry.name,
                    ))
                    removed_count += 1

            detection_time = (time.time() - start_time) * 1000

            report = ChangeReport(
                total_entries_before=len(before),
                total_entries_after=len(after),
                added_count=added_count,
                removed_count=removed_count,
                modified_count=modified_count,
                unchanged_count=unchanged_count,
                changes=changes,
                detection_time_ms=detection_time,
                hash_algorithm=self.algorithm,
            )

            logger.info(
                "World info change detection completed",
                extra={
                    "added": added_count,
                    "removed": removed_count,
                    "modified": modified_count,
                    "unchanged": unchanged_count,
                    "detection_time_ms": detection_time,
                }
            )

            return report

        except Exception as e:
            logger.error("World info change detection failed", extra={"error": str(e)})
            raise ChangeDetectionError(f"Failed to detect world info changes: {str(e)}")

    # ============================================
    # Dialog History Change Detection
    # ============================================

    def detect_dialog_changes(
        self,
        before: List[DialogTurn],
        after: List[DialogTurn]
    ) -> DialogDiff:
        """
        Detect changes between two dialog histories.

        Args:
            before: Previous dialog turns
            after: New dialog turns

        Returns:
            DialogDiff with detected changes

        Raises:
            ChangeDetectionError: If detection fails
        """
        try:
            logger.info(
                "Detecting dialog changes",
                extra={
                    "before_count": len(before),
                    "after_count": len(after)
                }
            )

            # Check structural changes
            turn_count_changed = len(before) != len(after)
            role_sequence_changed = self._check_role_sequence_change(before, after)

            # Build lookup dictionaries
            before_dict = {turn.turn_number: turn for turn in before}
            after_dict = {turn.turn_number: turn for turn in after}

            # Detect content changes
            content_changes = []

            # Check for added/modified/removed turns
            all_turn_numbers = set(before_dict.keys()) | set(after_dict.keys())

            for turn_number in sorted(all_turn_numbers):
                if turn_number in after_dict and turn_number not in before_dict:
                    # Turn added
                    new_turn = after_dict[turn_number]
                    content_changes.append(EntryChange(
                        change_type=ChangeType.ADDED,
                        entry_type="dialog",
                        identifier=f"turn_{turn_number}",
                        old_hash=None,
                        new_hash=new_turn.hash,
                        old_value=None,
                        new_value=self._serialize_dialog_turn(new_turn),
                        role=new_turn.role,
                        turn_number=turn_number,
                        content=new_turn.content,
                    ))
                elif turn_number in before_dict and turn_number not in after_dict:
                    # Turn removed
                    old_turn = before_dict[turn_number]
                    content_changes.append(EntryChange(
                        change_type=ChangeType.REMOVED,
                        entry_type="dialog",
                        identifier=f"turn_{turn_number}",
                        old_hash=old_turn.hash,
                        new_hash=None,
                        old_value=self._serialize_dialog_turn(old_turn),
                        new_value=None,
                        role=old_turn.role,
                        turn_number=turn_number,
                        content=old_turn.content,
                    ))
                else:
                    # Check if modified
                    old_turn = before_dict[turn_number]
                    new_turn = after_dict[turn_number]

                    if old_turn.hash != new_turn.hash:
                        content_changes.append(EntryChange(
                            change_type=ChangeType.MODIFIED,
                            entry_type="dialog",
                            identifier=f"turn_{turn_number}",
                            old_hash=old_turn.hash,
                            new_hash=new_turn.hash,
                            old_value=self._serialize_dialog_turn(old_turn),
                            new_value=self._serialize_dialog_turn(new_turn),
                            role=new_turn.role,
                            turn_number=turn_number,
                            content=new_turn.content,
                        ))

            # Generate summaries
            before_summary = self._summarize_dialog(before)
            after_summary = self._summarize_dialog(after)

            diff = DialogDiff(
                structural_changes=turn_count_changed or role_sequence_changed,
                turn_count_changed=turn_count_changed,
                role_sequence_changed=role_sequence_changed,
                content_changes=content_changes,
                before_summary=before_summary,
                after_summary=after_summary,
            )

            logger.info(
                "Dialog change detection completed",
                extra={
                    "structural_changes": diff.structural_changes,
                    "content_changes": len(content_changes),
                }
            )

            return diff

        except Exception as e:
            logger.error("Dialog change detection failed", extra={"error": str(e)})
            raise ChangeDetectionError(f"Failed to detect dialog changes: {str(e)}")

    # ============================================
    # Batch Change Detection
    # ============================================

    def batch_detect_world_info_changes(
        self,
        snapshots: List[List[WorldInfoEntry]]
    ) -> List[ChangeReport]:
        """
        Detect changes across multiple snapshots sequentially.

        Args:
            snapshots: List of world info entry snapshots in chronological order

        Returns:
            List of ChangeReport objects (one per transition)
        """
        if len(snapshots) < 2:
            return []

        reports = []

        for i in range(len(snapshots) - 1):
            report = self.detect_world_info_changes(snapshots[i], snapshots[i + 1])
            reports.append(report)

        return reports

    # ============================================
    # Helper Methods
    # ============================================

    def _build_world_info_lookup(
        self,
        entries: List[WorldInfoEntry]
    ) -> Dict[str, WorldInfoEntry]:
        """
        Build lookup dictionary for world info entries.

        Key: "{entry_type.value}:{name}"
        """
        return {f"{entry.entry_type.value}:{entry.name}": entry for entry in entries}

    def _serialize_world_info(self, entry: WorldInfoEntry) -> Dict[str, Any]:
        """Serialize world info entry for comparison."""
        return {
            "entry_type": entry.entry_type.value,
            "name": entry.name,
            "content": entry.content,
            "metadata": entry.metadata,
        }

    def _serialize_dialog_turn(self, turn: DialogTurn) -> Dict[str, Any]:
        """Serialize dialog turn for comparison."""
        return {
            "role": turn.role,
            "content": turn.content,
            "turn_number": turn.turn_number,
            "metadata": turn.metadata,
        }

    def _check_role_sequence_change(
        self,
        before: List[DialogTurn],
        after: List[DialogTurn]
    ) -> bool:
        """Check if role sequence changed between dialogs."""
        before_roles = [turn.role for turn in before]
        after_roles = [turn.role for turn in after]

        # Truncate to shorter length for comparison
        min_length = min(len(before_roles), len(after_roles))
        return before_roles[:min_length] != after_roles[:min_length]

    def _summarize_dialog(self, turns: List[DialogTurn]) -> Dict[str, int]:
        """Generate summary statistics for dialog."""
        summary = defaultdict(int)
        for turn in turns:
            summary[turn.role] += 1
        return dict(summary)
