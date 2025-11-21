"""Field-level retrieval cache to avoid redundant searches.

Caches field values keyed by product identifiers (name, CAS, UN) + field name.
Uses DuckDB for persistence with TTL-based expiration.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass

import duckdb

from ..utils.config import DATA_DIR
from ..utils.logger import logger

@dataclass
class CacheEntry:
    """Cached field value with metadata."""

    field_name: str
    value: str
    confidence: float
    source: str
    source_urls: list[str]
    cached_at: float
    hit_count: int = 0

class FieldCache:
    """Persistent cache for field retrieval results.

    Cache key is derived from:
    - Product name (if available)
    - CAS number (if available)
    - UN number (if available)
    - Field name

    This avoids redundant web searches when processing similar products
    or reprocessing the same document.
    """

    def __init__(self, ttl_seconds: int | None = None) -> None:
        """Initialize field cache.

        Args:
            ttl_seconds: Cache entry TTL (default: 30 days)
        """
        self.ttl = ttl_seconds or int(
            os.getenv("FIELD_CACHE_TTL", str(30 * 24 * 3600))
        )
        cache_dir = DATA_DIR / "duckdb"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(cache_dir / "field_cache.db")

        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.RLock()
        self._init_db()

        logger.info("Field cache initialized: ttl=%ds path=%s", self.ttl, self.db_path)

    def _init_db(self) -> None:
        """Initialize cache database schema."""
        with self._lock:
            self._conn = duckdb.connect(self.db_path)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS field_cache (
                    cache_key VARCHAR PRIMARY KEY,
                    field_name VARCHAR NOT NULL,
                    product_name VARCHAR,
                    cas_number VARCHAR,
                    un_number VARCHAR,
                    value TEXT NOT NULL,
                    confidence DOUBLE NOT NULL,
                    source VARCHAR,
                    source_urls TEXT,
                    cached_at BIGINT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                );
                """
            )
            # Index for efficient lookup
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cache_key
                ON field_cache(cache_key);
                """
            )
            # Index for cleanup queries
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cached_at
                ON field_cache(cached_at);
                """
            )
            logger.debug("Field cache schema initialized")

    def _generate_cache_key(
        self,
        field_name: str,
        product_name: str | None = None,
        cas_number: str | None = None,
        un_number: str | None = None,
    ) -> str:
        """Generate cache key from identifiers.

        Args:
            field_name: Field being retrieved
            product_name: Product name (normalized)
            cas_number: CAS number
            un_number: UN number

        Returns:
            SHA256 hash of normalized identifiers
        """
        # Normalize identifiers
        identifiers = []
        if product_name:
            identifiers.append(f"name:{product_name.lower().strip()}")
        if cas_number:
            identifiers.append(f"cas:{cas_number.strip()}")
        if un_number:
            identifiers.append(f"un:{un_number.strip()}")
        identifiers.append(f"field:{field_name}")

        # Generate hash
        key_str = "|".join(identifiers)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        field_name: str,
        product_name: str | None = None,
        cas_number: str | None = None,
        un_number: str | None = None,
    ) -> CacheEntry | None:
        """Retrieve cached field value if available and fresh.

        Args:
            field_name: Field being retrieved
            product_name: Product name
            cas_number: CAS number
            un_number: UN number

        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        if not self._conn:
            return None

        cache_key = self._generate_cache_key(
            field_name, product_name, cas_number, un_number
        )

        with self._lock:
            result = self._conn.execute(
                """
                SELECT
                    field_name, value, confidence, source,
                    source_urls, cached_at, hit_count
                FROM field_cache
                WHERE cache_key = ?
                """,
                [cache_key],
            ).fetchone()

            if not result:
                return None

            (
                fname,
                value,
                confidence,
                source,
                source_urls_json,
                cached_at,
                hit_count,
            ) = result

            # Check TTL
            age = time.time() - cached_at
            if age > self.ttl:
                logger.debug("Cache expired for key %s (age: %.1fs)", cache_key, age)
                # Optionally delete expired entry
                self._conn.execute(
                    "DELETE FROM field_cache WHERE cache_key = ?", [cache_key]
                )
                return None

            # Parse source_urls
            try:
                source_urls = json.loads(source_urls_json) if source_urls_json else []
            except Exception:  # noqa: BLE001
                source_urls = []

            # Increment hit count
            self._conn.execute(
                """
                UPDATE field_cache
                SET hit_count = hit_count + 1
                WHERE cache_key = ?
                """,
                [cache_key],
            )

            logger.debug(
                "Cache HIT for %s (key=%s, age=%.1fs, hits=%d)",
                field_name,
                cache_key[:8],
                age,
                hit_count + 1,
            )

            return CacheEntry(
                field_name=fname,
                value=value,
                confidence=confidence,
                source=source or "",
                source_urls=source_urls,
                cached_at=cached_at,
                hit_count=hit_count + 1,
            )

    def put(
        self,
        field_name: str,
        value: str,
        confidence: float,
        source: str = "",
        source_urls: list[str] | None = None,
        product_name: str | None = None,
        cas_number: str | None = None,
        un_number: str | None = None,
    ) -> None:
        """Store field value in cache.

        Args:
            field_name: Field name
            value: Field value
            confidence: Confidence score
            source: Source description
            source_urls: list of source URLs
            product_name: Product name for key generation
            cas_number: CAS number for key generation
            un_number: UN number for key generation
        """
        if not self._conn:
            return

        cache_key = self._generate_cache_key(
            field_name, product_name, cas_number, un_number
        )
        source_urls_json = json.dumps(source_urls) if source_urls else "[]"
        cached_at = int(time.time())

        with self._lock:
            # Upsert (insert or replace)
            self._conn.execute(
                """
                INSERT OR REPLACE INTO field_cache (
                    cache_key, field_name, product_name, cas_number, un_number,
                    value, confidence, source, source_urls, cached_at, hit_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                [
                    cache_key,
                    field_name,
                    product_name,
                    cas_number,
                    un_number,
                    value,
                    confidence,
                    source,
                    source_urls_json,
                    cached_at,
                ],
            )

            logger.debug(
                "Cache PUT for %s (key=%s, conf=%.2f)",
                field_name,
                cache_key[:8],
                confidence,
            )

    def invalidate(
        self,
        field_name: str,
        product_name: str | None = None,
        cas_number: str | None = None,
        un_number: str | None = None,
    ) -> bool:
        """Invalidate specific cache entry.

        Args:
            field_name: Field name
            product_name: Product name
            cas_number: CAS number
            un_number: UN number

        Returns:
            True if entry was found and deleted
        """
        if not self._conn:
            return False

        cache_key = self._generate_cache_key(
            field_name, product_name, cas_number, un_number
        )

        with self._lock:
            result = self._conn.execute(
                "DELETE FROM field_cache WHERE cache_key = ? RETURNING 1",
                [cache_key],
            ).fetchone()

            if result:
                logger.debug("Cache invalidated for key %s", cache_key[:8])
                return True
            return False

    def cleanup_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            Number of entries deleted
        """
        if not self._conn:
            return 0

        cutoff = int(time.time()) - self.ttl

        with self._lock:
            result = self._conn.execute(
                "DELETE FROM field_cache WHERE cached_at < ? RETURNING 1",
                [cutoff],
            ).fetchall()

            count = len(result)
            if count > 0:
                logger.info("Cleaned up %d expired cache entries", count)
            return count

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self._conn:
            return {}

        with self._lock:
            total_result = self._conn.execute(
                "SELECT COUNT(*) FROM field_cache"
            ).fetchone()
            total = total_result[0] if total_result else 0

            expired_result = self._conn.execute(
                "SELECT COUNT(*) FROM field_cache WHERE cached_at < ?",
                [int(time.time()) - self.ttl],
            ).fetchone()
            expired = expired_result[0] if expired_result else 0

            hits_result = self._conn.execute(
                "SELECT SUM(hit_count) FROM field_cache"
            ).fetchone()
            total_hits = (hits_result[0] if hits_result else 0) or 0

            return {
                "total_entries": total,
                "expired_entries": expired,
                "total_hits": total_hits,
                "hit_rate": total_hits / total if total > 0 else 0.0,
            }

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        if not self._conn:
            return 0

        with self._lock:
            result = self._conn.execute(
                "DELETE FROM field_cache RETURNING 1"
            ).fetchall()
            count = len(result)
            logger.info("Cleared field cache: %d entries deleted", count)
            return count

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

# Global cache instance
_global_cache: FieldCache | None = None
_cache_lock = threading.Lock()

def get_field_cache() -> FieldCache:
    """Get or create global field cache instance."""
    global _global_cache  # noqa: PLW0603
    with _cache_lock:
        if _global_cache is None:
            _global_cache = FieldCache()
        return _global_cache

__all__ = ["FieldCache", "CacheEntry", "get_field_cache"]
