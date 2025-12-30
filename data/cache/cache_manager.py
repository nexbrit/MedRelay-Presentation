"""
Cache Manager with SQLite backend and TTL support.

Provides efficient caching for market data with automatic expiration,
statistics tracking, and thread-safe operations.
"""

import sqlite3
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    SQLite-based cache manager with TTL support.

    Features:
    - Automatic cache expiration based on TTL
    - Thread-safe operations
    - Cache statistics (hit rate, miss rate)
    - Configurable cleanup intervals
    - JSON serialization for complex objects

    Example:
        cache = CacheManager()
        cache.set('quote:NIFTY', quote_data, ttl_seconds=5)
        data = cache.get('quote:NIFTY')  # Returns data if not expired
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        cleanup_interval_minutes: int = 5
    ):
        """
        Initialize cache manager.

        Args:
            db_path: Path to SQLite database. Defaults to data/cache/market_cache.db
            cleanup_interval_minutes: How often to clean expired entries
        """
        if db_path is None:
            cache_dir = Path(__file__).parent
            db_path = str(cache_dir / 'market_cache.db')

        self.db_path = db_path
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)
        self._last_cleanup = datetime.now()
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=10.0
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Main cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP
                    )
                ''')

                # Statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache_stats (
                        id INTEGER PRIMARY KEY,
                        total_hits INTEGER DEFAULT 0,
                        total_misses INTEGER DEFAULT 0,
                        total_sets INTEGER DEFAULT 0,
                        total_evictions INTEGER DEFAULT 0,
                        last_updated TIMESTAMP
                    )
                ''')

                # Insert initial stats row if not exists
                cursor.execute('''
                    INSERT OR IGNORE INTO cache_stats (id, last_updated)
                    VALUES (1, ?)
                ''', (datetime.now(),))

                # Index for expiration cleanup
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_expires_at
                    ON cache (expires_at)
                ''')

                conn.commit()
                logger.info(f"Cache database initialized at {self.db_path}")
            finally:
                conn.close()

    def _generate_key(self, key: str) -> str:
        """Generate a consistent cache key."""
        return hashlib.md5(key.encode()).hexdigest() if len(key) > 200 else key

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 60
    ) -> bool:
        """
        Store a value in cache with TTL.

        Args:
            key: Cache key (e.g., 'quote:NIFTY50')
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            self._maybe_cleanup()

            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                cache_key = self._generate_key(key)
                now = datetime.now()
                expires_at = now + timedelta(seconds=ttl_seconds)

                # Serialize value to JSON
                try:
                    value_json = json.dumps(value, default=str)
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to serialize cache value for {key}: {e}")
                    return False

                cursor.execute('''
                    INSERT OR REPLACE INTO cache
                    (key, value, created_at, expires_at, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, 0, NULL)
                ''', (cache_key, value_json, now, expires_at))

                # Update stats
                cursor.execute('''
                    UPDATE cache_stats
                    SET total_sets = total_sets + 1, last_updated = ?
                    WHERE id = 1
                ''', (now,))

                conn.commit()
                logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
                return True

            except sqlite3.Error as e:
                logger.error(f"Cache SET error for {key}: {e}")
                return False
            finally:
                conn.close()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache if not expired.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                cache_key = self._generate_key(key)
                now = datetime.now()

                cursor.execute('''
                    SELECT value FROM cache
                    WHERE key = ? AND expires_at > ?
                ''', (cache_key, now))

                row = cursor.fetchone()

                if row:
                    # Update access stats
                    cursor.execute('''
                        UPDATE cache
                        SET access_count = access_count + 1, last_accessed = ?
                        WHERE key = ?
                    ''', (now, cache_key))

                    cursor.execute('''
                        UPDATE cache_stats
                        SET total_hits = total_hits + 1, last_updated = ?
                        WHERE id = 1
                    ''', (now,))

                    conn.commit()

                    self._hits += 1
                    logger.debug(f"Cache HIT: {key}")

                    return json.loads(row['value'])
                else:
                    # Update miss stats
                    cursor.execute('''
                        UPDATE cache_stats
                        SET total_misses = total_misses + 1, last_updated = ?
                        WHERE id = 1
                    ''', (now,))

                    conn.commit()

                    self._misses += 1
                    logger.debug(f"Cache MISS: {key}")
                    return None

            except sqlite3.Error as e:
                logger.error(f"Cache GET error for {key}: {e}")
                return None
            finally:
                conn.close()

    def delete(self, key: str) -> bool:
        """
        Delete a specific key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cache_key = self._generate_key(key)

                cursor.execute('DELETE FROM cache WHERE key = ?', (cache_key,))
                conn.commit()

                deleted = cursor.rowcount > 0
                if deleted:
                    logger.debug(f"Cache DELETE: {key}")
                return deleted

            except sqlite3.Error as e:
                logger.error(f"Cache DELETE error for {key}: {e}")
                return False
            finally:
                conn.close()

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                cursor.execute('SELECT COUNT(*) as count FROM cache')
                count = cursor.fetchone()['count']

                cursor.execute('DELETE FROM cache')
                conn.commit()

                logger.info(f"Cache cleared: {count} entries removed")
                return count

            except sqlite3.Error as e:
                logger.error(f"Cache CLEAR error: {e}")
                return 0
            finally:
                conn.close()

    def _maybe_cleanup(self) -> None:
        """Periodically clean up expired entries."""
        now = datetime.now()
        if now - self._last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now

    def _cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()

            cursor.execute(
                'SELECT COUNT(*) as count FROM cache WHERE expires_at <= ?',
                (now,)
            )
            count = cursor.fetchone()['count']

            if count > 0:
                cursor.execute(
                    'DELETE FROM cache WHERE expires_at <= ?',
                    (now,)
                )

                cursor.execute('''
                    UPDATE cache_stats
                    SET total_evictions = total_evictions + ?, last_updated = ?
                    WHERE id = 1
                ''', (count, now))

                conn.commit()
                logger.debug(f"Cache cleanup: {count} expired entries removed")

            return count

        except sqlite3.Error as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit rate, miss rate, total entries, etc.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Get entry count
                cursor.execute('SELECT COUNT(*) as count FROM cache')
                entry_count = cursor.fetchone()['count']

                # Get expired count
                cursor.execute(
                    'SELECT COUNT(*) as count FROM cache WHERE expires_at <= ?',
                    (datetime.now(),)
                )
                expired_count = cursor.fetchone()['count']

                # Get stats
                cursor.execute('SELECT * FROM cache_stats WHERE id = 1')
                stats_row = cursor.fetchone()

                total_requests = (
                    stats_row['total_hits'] + stats_row['total_misses']
                ) if stats_row else 0

                hit_rate = (
                    stats_row['total_hits'] / total_requests * 100
                    if total_requests > 0 else 0.0
                )

                return {
                    'total_entries': entry_count,
                    'expired_entries': expired_count,
                    'total_hits': stats_row['total_hits'] if stats_row else 0,
                    'total_misses': stats_row['total_misses'] if stats_row else 0,
                    'total_sets': stats_row['total_sets'] if stats_row else 0,
                    'total_evictions': stats_row['total_evictions'] if stats_row else 0,
                    'hit_rate_percent': round(hit_rate, 2),
                    'session_hits': self._hits,
                    'session_misses': self._misses,
                    'last_updated': (
                        stats_row['last_updated'].isoformat()
                        if stats_row and stats_row['last_updated'] else None
                    )
                }

            except sqlite3.Error as e:
                logger.error(f"Cache stats error: {e}")
                return {}
            finally:
                conn.close()

    def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl_seconds: int = 60
    ) -> Optional[Any]:
        """
        Get value from cache, or compute and store it if not found.

        Args:
            key: Cache key
            factory: Callable to generate value if cache miss
            ttl_seconds: TTL for new cache entries

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        try:
            value = factory()
            if value is not None:
                self.set(key, value, ttl_seconds)
            return value
        except Exception as e:
            logger.error(f"Factory function failed for {key}: {e}")
            return None
