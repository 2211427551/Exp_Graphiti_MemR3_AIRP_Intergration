"""Unit tests for ChangeDetector service."""

import pytest
from app.services.change_detection import ChangeDetector
from app.services.hash_computation import HashComputationService
from app.models.change_detection import ChangeType, HashAlgorithm
from app.models.parsing import WorldInfoEntry, DialogTurn, WorldInfoType


class TestWorldInfoChangeDetection:
    """Test world info change detection."""

    @pytest.fixture
    def detector(self):
        """Create change detector."""
        hash_service = HashComputationService(algorithm=HashAlgorithm.MD5)
        return ChangeDetector(hash_service=hash_service)

    @pytest.fixture
    def sample_entries(self):
        """Create sample world info entries."""
        return [
            WorldInfoEntry(
                entry_type=WorldInfoType.LOCATION,
                name="天际省",
                content="天际省是泰姆瑞尔帝国的北部省份",
                hash="existing_hash_1"
            ),
            WorldInfoEntry(
                entry_type=WorldInfoType.FACTION,
                name="黑暗兄弟会",
                content="刺客组织",
                hash="existing_hash_2"
            ),
        ]

    def test_detect_added_entry(self, detector, sample_entries):
        """Test detecting added world info entry."""
        new_entry = WorldInfoEntry(
            entry_type=WorldInfoType.CHARACTER,
            name="Alice",
            content="冒险者",
        )
        new_entry.hash = detector.hash_service.compute_world_info_hash(
            new_entry.entry_type, new_entry.name, new_entry.content
        )

        after = sample_entries + [new_entry]
        report = detector.detect_world_info_changes(sample_entries, after)

        assert report.added_count == 1
        assert report.removed_count == 0
        assert report.modified_count == 0
        assert len(report.changes) == 1

        change = report.changes[0]
        assert change.change_type == ChangeType.ADDED
        assert change.name == "Alice"

    def test_detect_removed_entry(self, detector, sample_entries):
        """Test detecting removed world info entry."""
        before = sample_entries
        after = [sample_entries[0]]  # Remove second entry

        report = detector.detect_world_info_changes(before, after)

        assert report.added_count == 0
        assert report.removed_count == 1
        assert report.modified_count == 0

        change = report.changes[0]
        assert change.change_type == ChangeType.REMOVED
        assert change.name == "黑暗兄弟会"

    def test_detect_modified_entry(self, detector, sample_entries):
        """Test detecting modified world info entry."""
        # Modify first entry
        modified_entry = WorldInfoEntry(
            entry_type=sample_entries[0].entry_type,
            name=sample_entries[0].name,
            content="修改后的内容",  # Changed content
        )
        modified_entry.hash = detector.hash_service.compute_world_info_hash(
            modified_entry.entry_type, modified_entry.name, modified_entry.content
        )

        after = [modified_entry, sample_entries[1]]
        report = detector.detect_world_info_changes(sample_entries, after)

        assert report.added_count == 0
        assert report.removed_count == 0
        assert report.modified_count == 1

        change = report.changes[0]
        assert change.change_type == ChangeType.MODIFIED
        assert change.name == "天际省"
        assert change.old_hash != change.new_hash

    def test_detect_unchanged_entries(self, detector, sample_entries):
        """Test detecting unchanged entries."""
        report = detector.detect_world_info_changes(sample_entries, sample_entries)

        assert report.added_count == 0
        assert report.removed_count == 0
        assert report.modified_count == 0
        assert report.unchanged_count == 2
        assert len(report.changes) == 0

    def test_detect_multiple_changes(self, detector, sample_entries):
        """Test detecting multiple types of changes."""
        # Add one
        new_entry = WorldInfoEntry(
            entry_type=WorldInfoType.CHARACTER,
            name="Alice",
            content="冒险者",
        )
        new_entry.hash = detector.hash_service.compute_world_info_hash(
            new_entry.entry_type, new_entry.name, new_entry.content
        )

        # Modify one
        modified_entry = WorldInfoEntry(
            entry_type=sample_entries[0].entry_type,
            name=sample_entries[0].name,
            content="修改后的内容",
        )
        modified_entry.hash = detector.hash_service.compute_world_info_hash(
            modified_entry.entry_type, modified_entry.name, modified_entry.content
        )

        after = [modified_entry, sample_entries[1], new_entry]
        report = detector.detect_world_info_changes(sample_entries, after)

        assert report.added_count == 1
        assert report.removed_count == 0
        assert report.modified_count == 1
        assert report.unchanged_count == 1


class TestDialogChangeDetection:
    """Test dialog history change detection."""

    @pytest.fixture
    def detector(self):
        """Create change detector."""
        hash_service = HashComputationService(algorithm=HashAlgorithm.MD5)
        return ChangeDetector(hash_service=hash_service)

    @pytest.fixture
    def sample_dialog(self, detector):
        """Create sample dialog turns."""
        turns = [
            DialogTurn(role="user", content="你好", turn_number=0),
            DialogTurn(role="assistant", content="你好！", turn_number=1),
            DialogTurn(role="user", content="告诉我关于天际省的信息", turn_number=2),
        ]

        # Compute hashes
        for turn in turns:
            turn.hash = detector.hash_service.compute_dialog_turn_hash(
                turn.role, turn.content, turn.turn_number
            )

        return turns

    def test_detect_turn_count_change(self, detector, sample_dialog):
        """Test detecting turn count change."""
        new_turn = DialogTurn(
            role="assistant",
            content="天际省位于泰姆瑞尔北部",
            turn_number=3
        )
        new_turn.hash = detector.hash_service.compute_dialog_turn_hash(
            new_turn.role, new_turn.content, new_turn.turn_number
        )

        after = sample_dialog + [new_turn]
        diff = detector.detect_dialog_changes(sample_dialog, after)

        assert diff.turn_count_changed is True
        assert diff.structural_changes is True

    def test_detect_role_sequence_change(self, detector, sample_dialog):
        """Test detecting role sequence change."""
        # Change role of second turn
        modified_turn = DialogTurn(
            role="user",  # Changed from assistant
            content="你好！",
            turn_number=1
        )
        modified_turn.hash = detector.hash_service.compute_dialog_turn_hash(
            modified_turn.role, modified_turn.content, modified_turn.turn_number
        )

        after = [sample_dialog[0], modified_turn, sample_dialog[2]]
        diff = detector.detect_dialog_changes(sample_dialog, after)

        assert diff.role_sequence_changed is True
        assert diff.structural_changes is True

    def test_detect_content_change(self, detector, sample_dialog):
        """Test detecting content change in turn."""
        # Modify content of second turn
        modified_turn = DialogTurn(
            role=sample_dialog[1].role,
            content="修改后的回答",  # Changed content
            turn_number=sample_dialog[1].turn_number
        )
        modified_turn.hash = detector.hash_service.compute_dialog_turn_hash(
            modified_turn.role, modified_turn.content, modified_turn.turn_number
        )

        after = [sample_dialog[0], modified_turn, sample_dialog[2]]
        diff = detector.detect_dialog_changes(sample_dialog, after)

        assert diff.turn_count_changed is False
        assert diff.role_sequence_changed is False
        assert diff.structural_changes is False
        assert len(diff.content_changes) == 1

        change = diff.content_changes[0]
        assert change.change_type == ChangeType.MODIFIED
        assert change.turn_number == 1

    def test_dialog_summary(self, detector, sample_dialog):
        """Test dialog summary generation."""
        diff = detector.detect_dialog_changes(sample_dialog, sample_dialog)

        assert diff.before_summary["user"] == 2
        assert diff.before_summary["assistant"] == 1
        assert diff.after_summary == diff.before_summary  # No changes


class TestBatchChangeDetection:
    """Test batch change detection."""

    def test_batch_detect_world_info_changes(self):
        """Test detecting changes across multiple snapshots."""
        import copy
        detector = ChangeDetector()

        # Create 3 snapshots
        snapshot1 = [
            WorldInfoEntry(
                entry_type=WorldInfoType.LOCATION,
                name="地点1",
                content="描述1",
            )
        ]
        snapshot1[0].hash = detector.hash_service.compute_world_info_hash(
            snapshot1[0].entry_type, snapshot1[0].name, snapshot1[0].content
        )

        snapshot2 = copy.deepcopy(snapshot1)
        new_entry = WorldInfoEntry(
            entry_type=WorldInfoType.LOCATION,
            name="地点2",
            content="描述2",
        )
        new_entry.hash = detector.hash_service.compute_world_info_hash(
            new_entry.entry_type, new_entry.name, new_entry.content
        )
        snapshot2.append(new_entry)

        snapshot3 = copy.deepcopy(snapshot2)
        snapshot3[0].content = "修改后的描述"
        snapshot3[0].hash = detector.hash_service.compute_world_info_hash(
            snapshot3[0].entry_type, snapshot3[0].name, snapshot3[0].content
        )

        snapshots = [snapshot1, snapshot2, snapshot3]
        reports = detector.batch_detect_world_info_changes(snapshots)

        assert len(reports) == 2

        # First transition: 1 added
        assert reports[0].added_count == 1
        assert reports[0].modified_count == 0

        # Second transition: 1 modified
        assert reports[1].added_count == 0
        assert reports[1].modified_count == 1
