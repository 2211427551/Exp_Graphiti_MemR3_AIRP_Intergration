"""Integration tests for change detection system."""

import pytest
import time
from app.services.parser.world_info_parser import WorldInfoParser
from app.services.change_detection import ChangeDetector
from app.services.hash_computation import HashComputationService
from app.models.change_detection import HashAlgorithm
from app.models.parsing import WorldInfoType, WorldInfoEntry


@pytest.mark.asyncio
async def test_full_pipeline_change_detection():
    """Test complete pipeline: parse -> hash -> detect changes."""
    # Initialize services
    parser = WorldInfoParser(compute_hashes=True)
    detector = ChangeDetector()

    # First version
    content_v1 = """
    地点("天际省")["天际省是泰姆瑞尔帝国的北部省份"]
    派系("黑暗兄弟会")["刺客组织"]
    """

    # Second version (one added, one modified, one unchanged)
    content_v2 = """
    地点("天际省")["天际省是泰姆瑞尔帝国的北部省份，首府是独孤城"]
    派系("黑暗兄弟会")["刺客组织"]
    角色("Alice")["冒险者"]
    """

    # Parse both versions
    entries_v1 = await parser.parse_world_info(content_v1)
    entries_v2 = await parser.parse_world_info(content_v2)

    # Detect changes
    report = detector.detect_world_info_changes(entries_v1, entries_v2)

    # Verify results
    assert report.added_count == 1  # Alice
    assert report.modified_count == 1  # 天际省
    assert report.unchanged_count == 1  # 黑暗兄弟会
    assert report.total_entries_before == 2
    assert report.total_entries_after == 3


@pytest.mark.asyncio
async def test_dialog_history_change_detection():
    """Test dialog history change detection through parser."""
    parser = WorldInfoParser(compute_hashes=True)
    detector = ChangeDetector()

    # First dialog
    dialog_v1 = """
    user: 你好
    assistant: 你好！有什么我可以帮助你的吗？
    user: 告诉我关于天际省的信息
    """

    # Second dialog (one turn modified, one added)
    dialog_v2 = """
    user: 你好
    assistant: 你好！很高兴为你服务。
    user: 告诉我关于天际省的信息
    assistant: 天际省是泰姆瑞尔帝国的北部省份。
    """

    # Parse both dialogs
    turns_v1 = parser.parse_dialog_history(dialog_v1)
    turns_v2 = parser.parse_dialog_history(dialog_v2)

    # Detect changes
    diff = detector.detect_dialog_changes(turns_v1, turns_v2)

    # Verify results
    assert diff.turn_count_changed is True  # 3 turns -> 4 turns
    assert len(diff.content_changes) > 0


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_performance_large_scale_change_detection():
    """Benchmark change detection performance on large datasets."""
    parser = WorldInfoParser(compute_hashes=True)
    detector = ChangeDetector()

    # Generate large dataset (1000 entries)
    entries_v1 = []
    entries_v2 = []

    for i in range(1000):
        entry = WorldInfoEntry(
            entry_type=WorldInfoType.LOCATION,
            name=f"地点{i}",
            content=f"这是地点{i}的描述",
        )
        entry.hash = detector.hash_service.compute_world_info_hash(
            entry.entry_type, entry.name, entry.content
        )
        entries_v1.append(entry)

        # Modify 10% of entries in v2
        if i % 10 == 0:
            entry = WorldInfoEntry(
                entry_type=WorldInfoType.LOCATION,
                name=f"地点{i}",
                content=f"这是修改后的地点{i}的描述",
            )
            entry.hash = detector.hash_service.compute_world_info_hash(
                entry.entry_type, entry.name, entry.content
            )
            entries_v2.append(entry)
        else:
            # Use the same entry from v1 (no modification)
            entries_v2.append(entries_v1[i])

    # Benchmark change detection
    start_time = time.time()
    report = detector.detect_world_info_changes(entries_v1, entries_v2)
    detection_time = time.time() - start_time

    # Verify correctness
    assert report.modified_count == 100  # 10% of 1000
    assert report.unchanged_count == 900

    # Performance assertions
    # Should complete in less than 1 second for 1000 entries
    assert detection_time < 1.0

    # Log performance
    print(f"\nChange detection for 1000 entries: {detection_time:.4f}s")
    print(f"Throughput: {1000 / detection_time:.0f} entries/second")


@pytest.mark.benchmark
def test_hash_algorithm_comparison():
    """Compare performance of different hash algorithms."""
    content = "test content" * 100  # ~1.2 KB
    iterations = 10000

    results = {}

    for algorithm in [HashAlgorithm.MD5, HashAlgorithm.SHA256]:
        service = HashComputationService(algorithm=algorithm)

        start_time = time.time()
        for _ in range(iterations):
            service.compute_hash(content)
        elapsed = time.time() - start_time

        results[algorithm.value] = {
            "time": elapsed,
            "hashes_per_second": iterations / elapsed
        }

    # Print comparison
    print("\nHash Algorithm Performance Comparison:")
    for alg, stats in results.items():
        print(f"{alg}: {stats['hashes_per_second']:.0f} hashes/second")

    # Both algorithms should be fast enough (>500K hashes/sec)
    # Note: On modern systems with hardware acceleration, SHA256 can be as fast as MD5
    assert results["md5"]["hashes_per_second"] > 500000
    assert results["sha256"]["hashes_per_second"] > 500000


@pytest.mark.asyncio
async def test_backward_compatibility_with_existing_hashes():
    """Test that new system is compatible with existing MD5 hashes."""
    import hashlib

    # Simulate existing hash (computed old way)
    entry_type = WorldInfoType.LOCATION
    name = "天际省"
    content = "天际省是泰姆瑞尔帝国的北部省份"

    old_content = f"{entry_type.value}:{name}:{content}"
    existing_hash = hashlib.md5(old_content.encode('utf-8')).hexdigest()

    # Create entry with existing hash
    old_entry = WorldInfoEntry(
        entry_type=entry_type,
        name=name,
        content=content,
        hash=existing_hash
    )

    # Parse new version (should use new service)
    parser = WorldInfoParser(compute_hashes=True)
    new_content = f'地点("{name}")["{content}"]'
    new_entries = await parser.parse_world_info(new_content)
    new_entry = new_entries[0]

    # Hashes should match exactly
    assert old_entry.hash == new_entry.hash

    # Change detection should recognize they're the same
    detector = ChangeDetector()
    report = detector.detect_world_info_changes([old_entry], [new_entry])

    assert report.modified_count == 0
    assert report.unchanged_count == 1


@pytest.mark.asyncio
async def test_change_detection_with_cache():
    """Test change detection with caching enabled."""
    # Service with cache
    hash_service = HashComputationService(
        algorithm=HashAlgorithm.MD5,
        enable_cache=True,
        cache_size=100
    )
    detector = ChangeDetector(hash_service=hash_service)

    # Parse and hash entries (use same hash_service for cache to work)
    parser = WorldInfoParser(compute_hashes=True, hash_service=hash_service)
    content = """
    地点("天际省")["天际省是泰姆瑞尔帝国的北部省份"]
    派系("黑暗兄弟会")["刺客组织"]
    """

    entries_v1 = await parser.parse_world_info(content)
    entries_v2 = await parser.parse_world_info(content)

    # Detect changes (should use cache for second version)
    report = detector.detect_world_info_changes(entries_v1, entries_v2)

    # Check cache stats
    stats = hash_service.get_stats()
    assert stats.cache_hits > 0  # Should have cache hits
    assert report.unchanged_count == 2  # No changes
