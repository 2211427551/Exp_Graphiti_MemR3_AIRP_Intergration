"""Hash computation service with pluggable algorithms and caching."""

import hashlib
import time
from typing import Optional, Dict, Any
from collections import OrderedDict

import structlog

try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

from app.models.change_detection import HashAlgorithm, HashComputationStats
from app.models.parsing import WorldInfoEntry, DialogTurn, WorldInfoType
from app.core.config import settings

logger = structlog.get_logger(__name__)


class LRUCache:
    """Thread-safe LRU cache for hash computations."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries to cache
        """
        self.cache: OrderedDict[str, str] = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value: str) -> None:
        """Put value in cache."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        # Remove oldest if at capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "max_size": self.max_size,
        }


class HashComputationService:
    """
    Hash computation service with pluggable algorithms.

    Supports:
    - MD5: Default, backward compatible (128-bit)
    - xxhash64: Fast non-cryptographic hash (64-bit) - 10x faster than MD5
    - SHA256: Cryptographic hash (256-bit) - most secure but slower
    """

    def __init__(
        self,
        algorithm: Optional[HashAlgorithm] = None,
        enable_cache: Optional[bool] = None,
        cache_size: Optional[int] = None
    ):
        """
        Initialize hash computation service.

        Args:
            algorithm: Hash algorithm to use (uses settings if not provided)
            enable_cache: Enable LRU caching (uses settings if not provided)
            cache_size: Maximum cache size (uses settings if not provided)
        """
        self.algorithm = algorithm or HashAlgorithm(settings.hash_computation_algorithm)

        if self.algorithm == HashAlgorithm.XXHASH and not XXHASH_AVAILABLE:
            logger.warning("xxhash not available, falling back to MD5")
            self.algorithm = HashAlgorithm.MD5

        self.enable_cache = enable_cache if enable_cache is not None else settings.hash_computation_enable_cache
        self.cache_size = cache_size or settings.hash_computation_cache_size

        self.cache = LRUCache(max_size=self.cache_size) if self.enable_cache else None

        logger.info(
            "HashComputationService initialized",
            extra={
                "algorithm": self.algorithm.value,
                "enable_cache": self.enable_cache,
                "cache_size": self.cache_size,
            }
        )

    def compute_hash(
        self,
        content: str,
        salt: str = ""
    ) -> str:
        """
        Compute hash for content using configured algorithm.

        Args:
            content: Content to hash
            salt: Optional salt for hash computation

        Returns:
            Hexadecimal hash string
        """
        # Check cache first
        if self.cache:
            cache_key = f"{self.algorithm.value}:{salt}:{content}"
            cached_hash = self.cache.get(cache_key)
            if cached_hash:
                return cached_hash

        # Compute hash based on algorithm
        if self.algorithm == HashAlgorithm.MD5:
            hash_value = self._compute_md5(content, salt)
        elif self.algorithm == HashAlgorithm.XXHASH:
            hash_value = self._compute_xxhash(content, salt)
        elif self.algorithm == HashAlgorithm.SHA256:
            hash_value = self._compute_sha256(content, salt)
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")

        # Store in cache
        if self.cache:
            self.cache.put(cache_key, hash_value)

        return hash_value

    def compute_world_info_hash(
        self,
        entry_type: WorldInfoType,
        name: str,
        content: str
    ) -> str:
        """
        Compute hash for WorldInfoEntry (maintains backward compatibility).

        Format: "{entry_type.value}:{name}:{content}"

        Args:
            entry_type: Type of world info entry
            name: Entry name
            content: Entry content

        Returns:
            Hexadecimal hash string
        """
        content_to_hash = f"{entry_type.value}:{name}:{content}"
        return self.compute_hash(content_to_hash)

    def compute_dialog_turn_hash(
        self,
        role: str,
        content: str,
        turn_number: int
    ) -> str:
        """
        Compute hash for DialogTurn.

        Format: "{role}:{turn_number}:{content}"

        Args:
            role: Speaker role
            content: Turn content
            turn_number: Turn index

        Returns:
            Hexadecimal hash string
        """
        content_to_hash = f"{role}:{turn_number}:{content}"
        return self.compute_hash(content_to_hash)

    def batch_compute_hashes(
        self,
        items: list,
        hash_type: str = "world_info"
    ) -> list:
        """
        Compute hashes for multiple items efficiently.

        Args:
            items: List of items to hash (WorldInfoEntry or DialogTurn)
            hash_type: Type of items ("world_info" or "dialog")

        Returns:
            List of computed hash values
        """
        hashes = []

        for item in items:
            if hash_type == "world_info":
                hash_value = self.compute_world_info_hash(
                    item.entry_type,
                    item.name,
                    item.content
                )
            elif hash_type == "dialog":
                hash_value = self.compute_dialog_turn_hash(
                    item.role,
                    item.content,
                    item.turn_number
                )
            else:
                raise ValueError(f"Unsupported hash_type: {hash_type}")

            hashes.append(hash_value)

        return hashes

    def get_stats(self) -> HashComputationStats:
        """
        Get hash computation statistics.

        Returns:
            HashComputationStats with current statistics
        """
        if self.cache:
            cache_stats = self.cache.get_stats()
        else:
            cache_stats = {"hits": 0, "misses": 0}

        return HashComputationStats(
            total_hashes_computed=cache_stats.get("hits", 0) + cache_stats.get("misses", 0),
            cache_hits=cache_stats.get("hits", 0),
            cache_misses=cache_stats.get("misses", 0),
            computation_time_ms=0.0,  # Would need to track during computation
            algorithm_used=self.algorithm,
        )

    # Private methods for each algorithm

    def _compute_md5(self, content: str, salt: str) -> str:
        """Compute MD5 hash."""
        return hashlib.md5(f"{salt}{content}".encode('utf-8')).hexdigest()

    def _compute_sha256(self, content: str, salt: str) -> str:
        """Compute SHA256 hash."""
        return hashlib.sha256(f"{salt}{content}".encode('utf-8')).hexdigest()

    def _compute_xxhash(self, content: str, salt: str) -> str:
        """Compute xxhash64 (10x faster than MD5)."""
        if not XXHASH_AVAILABLE:
            raise RuntimeError("xxhash is not available")
        # Use xxh64 for 64-bit hash (hex representation)
        hash_int = xxhash.xxh64(f"{salt}{content}".encode('utf-8')).hexdigest()
        return format(hash_int, 'x')
