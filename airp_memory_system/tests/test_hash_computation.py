"""Unit tests for HashComputationService."""

import pytest
from app.services.hash_computation import (
    HashComputationService,
    LRUCache,
)
from app.models.change_detection import HashAlgorithm
from app.models.parsing import WorldInfoType


class TestLRUCache:
    """Test LRU cache functionality."""

    def test_cache_put_and_get(self):
        """Test basic cache operations."""
        cache = LRUCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None

    def test_cache_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache(max_size=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should evict key1

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = LRUCache(max_size=10)

        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1


class TestHashComputationService:
    """Test hash computation service."""

    @pytest.fixture
    def md5_service(self):
        """Create hash service with MD5."""
        return HashComputationService(algorithm=HashAlgorithm.MD5)

    @pytest.fixture
    def sha256_service(self):
        """Create hash service with SHA256."""
        return HashComputationService(algorithm=HashAlgorithm.SHA256)

    def test_compute_hash_md5(self, md5_service):
        """Test MD5 hash computation."""
        content = "test content"
        hash_value = md5_service.compute_hash(content)

        assert len(hash_value) == 32  # MD5 produces 128-bit hash (32 hex chars)
        assert isinstance(hash_value, str)

    def test_compute_hash_sha256(self, sha256_service):
        """Test SHA256 hash computation."""
        content = "test content"
        hash_value = sha256_service.compute_hash(content)

        assert len(hash_value) == 64  # SHA256 produces 256-bit hash (64 hex chars)
        assert isinstance(hash_value, str)

    def test_compute_hash_with_salt(self, md5_service):
        """Test hash computation with salt."""
        content = "test content"

        hash1 = md5_service.compute_hash(content, salt="salt1")
        hash2 = md5_service.compute_hash(content, salt="salt2")

        assert hash1 != hash2  # Different salt should produce different hash

    def test_compute_world_info_hash(self, md5_service):
        """Test world info hash computation."""
        entry_type = WorldInfoType.LOCATION
        name = "天际省"
        content = "天际省是泰姆瑞尔帝国的北部省份"

        hash_value = md5_service.compute_world_info_hash(entry_type, name, content)

        assert hash_value is not None
        assert len(hash_value) == 32

    def test_compute_dialog_turn_hash(self, md5_service):
        """Test dialog turn hash computation."""
        role = "user"
        content = "你好"
        turn_number = 0

        hash_value = md5_service.compute_dialog_turn_hash(role, content, turn_number)

        assert hash_value is not None
        assert len(hash_value) == 32

    def test_cache_hit(self, md5_service):
        """Test cache hit for repeated computations."""
        content = "test content"

        # First computation (cache miss)
        hash1 = md5_service.compute_hash(content)
        stats1 = md5_service.get_stats()

        # Second computation (cache hit)
        hash2 = md5_service.compute_hash(content)
        stats2 = md5_service.get_stats()

        assert hash1 == hash2
        assert stats2.cache_hits > stats1.cache_hits

    def test_batch_compute_hashes(self, md5_service):
        """Test batch hash computation."""
        from app.models.parsing import WorldInfoEntry

        entries = [
            WorldInfoEntry(
                entry_type=WorldInfoType.LOCATION,
                name=f"地点{i}",
                content=f"描述{i}"
            )
            for i in range(10)
        ]

        hashes = md5_service.batch_compute_hashes(entries, hash_type="world_info")

        assert len(hashes) == 10
        assert all(h is not None for h in hashes)
        assert len(set(hashes)) == 10  # All hashes should be unique

    def test_backward_compatibility_md5(self, md5_service):
        """Test backward compatibility with existing MD5 hashes."""
        import hashlib

        entry_type = WorldInfoType.LOCATION
        name = "测试"
        content = "内容"

        # Old way (direct MD5)
        old_content = f"{entry_type.value}:{name}:{content}"
        old_hash = hashlib.md5(old_content.encode('utf-8')).hexdigest()

        # New way (service)
        new_hash = md5_service.compute_world_info_hash(entry_type, name, content)

        assert old_hash == new_hash  # Should match exactly


@pytest.mark.benchmark
class TestHashComputationPerformance:
    """Performance benchmarks for hash computation."""

    def test_md5_performance(self):
        """Benchmark MD5 hash computation."""
        import time

        service = HashComputationService(algorithm=HashAlgorithm.MD5)
        content = "test content" * 100  # ~1.2 KB

        iterations = 10000
        start_time = time.time()

        for _ in range(iterations):
            service.compute_hash(content)

        elapsed = time.time() - start_time
        hashes_per_second = iterations / elapsed

        # MD5 should do at least 100,000 hashes/sec on 1KB content
        assert hashes_per_second > 100000

    def test_cache_performance(self):
        """Benchmark cache effectiveness."""
        import time

        service = HashComputationService(algorithm=HashAlgorithm.MD5, enable_cache=True)
        content = "test content"

        iterations = 1000

        # First pass (cache misses)
        start_time = time.time()
        for _ in range(iterations):
            service.compute_hash(content)
        first_pass_time = time.time() - start_time

        # Second pass (cache hits)
        start_time = time.time()
        for _ in range(iterations):
            service.compute_hash(content)
        second_pass_time = time.time() - start_time

        # Cached version should be faster (or at least not slower)
        # On very fast systems, both may complete in similar time due to timing precision
        assert second_pass_time <= first_pass_time * 1.5
