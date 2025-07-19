"""
Enhanced caching layer for eBay API responses.

Implements a hybrid caching strategy with Redis and in-memory fallback,
intelligent TTL management, and cache invalidation patterns.
"""
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    redis_hits: int = 0
    memory_hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.redis_hits + self.memory_hits + self.misses
        if total == 0:
            return 0.0
        return (self.redis_hits + self.memory_hits) / total
    
    @property
    def redis_hit_rate(self) -> float:
        """Calculate Redis hit rate."""
        total = self.redis_hits + self.memory_hits + self.misses
        if total == 0:
            return 0.0
        return self.redis_hits / total


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "value": self.value,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            value=data["value"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            access_count=data["access_count"]
        )


class CacheInterface(ABC):
    """Interface for cache implementations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache with TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass


class MemoryCache(CacheInterface):
    """In-memory cache implementation with TTL support."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                return None
            
            entry.access_count += 1
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in memory cache."""
        async with self._lock:
            # Evict expired entries if at capacity
            if len(self._cache) >= self.max_size:
                await self._evict_expired()
                
                # If still at capacity, evict least recently used
                if len(self._cache) >= self.max_size:
                    await self._evict_lru()
            
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            entry = CacheEntry(value=value, expires_at=expires_at)
            self._cache[key] = entry
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (simple prefix matching)."""
        async with self._lock:
            # Simple pattern matching - just prefix for now
            prefix = pattern.rstrip('*')
            to_delete = [key for key in self._cache.keys() if key.startswith(prefix)]
            
            for key in to_delete:
                del self._cache[key]
            
            return len(to_delete)
    
    async def clear(self) -> bool:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()
            return True
    
    async def _evict_expired(self):
        """Remove expired entries."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.expires_at <= now
        ]
        
        for key in expired_keys:
            del self._cache[key]
    
    async def _evict_lru(self):
        """Remove least recently used entries."""
        if not self._cache:
            return
        
        # Sort by access count (ascending) and creation time
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: (x[1].access_count, x[1].created_at)
        )
        
        # Remove 10% of entries
        to_remove = max(1, len(sorted_items) // 10)
        for key, _ in sorted_items[:to_remove]:
            del self._cache[key]
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class RedisCache(CacheInterface):
    """Redis cache implementation."""
    
    def __init__(self, redis_url: str, key_prefix: str = "lootly:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client = None
        self._lock = asyncio.Lock()
    
    async def _get_client(self):
        """Get Redis client with connection pooling."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = redis.from_url(
                        self.redis_url,
                        decode_responses=True,
                        max_connections=20
                    )
        return self._client
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key)
            
            data = await client.get(prefixed_key)
            if data is None:
                return None
            
            # Parse JSON data
            entry_data = json.loads(data)
            entry = CacheEntry.from_dict(entry_data)
            
            # Check if expired
            if entry.is_expired():
                await client.delete(prefixed_key)
                return None
            
            return entry.value
            
        except Exception as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in Redis cache."""
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key)
            
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            entry = CacheEntry(value=value, expires_at=expires_at)
            
            # Serialize entry
            data = json.dumps(entry.to_dict())
            
            # Set with TTL
            await client.setex(prefixed_key, ttl, data)
            return True
            
        except Exception as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key)
            
            result = await client.delete(prefixed_key)
            return result > 0
            
        except Exception as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            client = await self._get_client()
            prefixed_pattern = self._make_key(pattern)
            
            # Get matching keys
            keys = await client.keys(prefixed_pattern)
            
            if keys:
                result = await client.delete(*keys)
                return result
            
            return 0
            
        except Exception as e:
            logger.warning(f"Redis delete_pattern error for pattern {pattern}: {e}")
            return 0
    
    async def clear(self) -> bool:
        """Clear all cache entries with prefix."""
        try:
            client = await self._get_client()
            pattern = f"{self.key_prefix}*"
            
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
            
            return True
            
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()


class HybridCacheManager:
    """
    Hybrid caching manager with Redis and in-memory fallback.
    
    Implements L1 (memory) and L2 (Redis) cache hierarchy with
    intelligent fallback and performance monitoring.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        memory_max_size: int = 1000,
        key_prefix: str = "lootly:"
    ):
        self.memory_cache = MemoryCache(max_size=memory_max_size)
        self.redis_cache = None
        self.stats = CacheStats()
        
        # Initialize Redis cache if URL provided
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_cache = RedisCache(redis_url, key_prefix)
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
        
        if not self.redis_cache:
            logger.info("Using memory-only cache")
    
    def _make_cache_key(self, key: str) -> str:
        """Create normalized cache key."""
        # Hash long keys to avoid Redis key length limits
        if len(key) > 250:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            return f"hash:{key_hash}"
        return key
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with L1 -> L2 fallback.
        
        Checks memory cache first, then Redis cache.
        """
        cache_key = self._make_cache_key(key)
        
        # Try L1 cache (memory) first
        try:
            value = await self.memory_cache.get(cache_key)
            if value is not None:
                self.stats.memory_hits += 1
                return value
        except Exception as e:
            logger.warning(f"Memory cache get error: {e}")
            self.stats.errors += 1
        
        # Try L2 cache (Redis) if available
        if self.redis_cache:
            try:
                value = await self.redis_cache.get(cache_key)
                if value is not None:
                    self.stats.redis_hits += 1
                    
                    # Backfill L1 cache
                    await self.memory_cache.set(cache_key, value, 3600)  # 1 hour
                    return value
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
                self.stats.errors += 1
        
        # Cache miss
        self.stats.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set value in both caches with TTL.
        
        Writes to both L1 and L2 caches for consistency.
        """
        cache_key = self._make_cache_key(key)
        success = False
        
        # Set in L1 cache (memory)
        try:
            memory_ttl = min(ttl, 3600)  # Max 1 hour for memory
            await self.memory_cache.set(cache_key, value, memory_ttl)
            success = True
        except Exception as e:
            logger.warning(f"Memory cache set error: {e}")
            self.stats.errors += 1
        
        # Set in L2 cache (Redis) if available
        if self.redis_cache:
            try:
                await self.redis_cache.set(cache_key, value, ttl)
                success = True
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
                self.stats.errors += 1
        
        if success:
            self.stats.sets += 1
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete key from all caches."""
        cache_key = self._make_cache_key(key)
        success = False
        
        # Delete from L1 cache
        try:
            if await self.memory_cache.delete(cache_key):
                success = True
        except Exception as e:
            logger.warning(f"Memory cache delete error: {e}")
            self.stats.errors += 1
        
        # Delete from L2 cache
        if self.redis_cache:
            try:
                if await self.redis_cache.delete(cache_key):
                    success = True
            except Exception as e:
                logger.warning(f"Redis cache delete error: {e}")
                self.stats.errors += 1
        
        if success:
            self.stats.deletes += 1
        
        return success
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern from all caches."""
        total_deleted = 0
        
        # Delete from L1 cache
        try:
            deleted = await self.memory_cache.delete_pattern(pattern)
            total_deleted += deleted
        except Exception as e:
            logger.warning(f"Memory cache delete_pattern error: {e}")
            self.stats.errors += 1
        
        # Delete from L2 cache
        if self.redis_cache:
            try:
                deleted = await self.redis_cache.delete_pattern(pattern)
                total_deleted += deleted
            except Exception as e:
                logger.warning(f"Redis cache delete_pattern error: {e}")
                self.stats.errors += 1
        
        if total_deleted > 0:
            self.stats.deletes += total_deleted
        
        return total_deleted
    
    async def clear(self) -> bool:
        """Clear all caches."""
        success = False
        
        # Clear L1 cache
        try:
            await self.memory_cache.clear()
            success = True
        except Exception as e:
            logger.warning(f"Memory cache clear error: {e}")
            self.stats.errors += 1
        
        # Clear L2 cache
        if self.redis_cache:
            try:
                await self.redis_cache.clear()
                success = True
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")
                self.stats.errors += 1
        
        return success
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "redis_hits": self.stats.redis_hits,
            "memory_hits": self.stats.memory_hits,
            "misses": self.stats.misses,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "errors": self.stats.errors,
            "hit_rate": self.stats.hit_rate,
            "redis_hit_rate": self.stats.redis_hit_rate,
            "memory_cache_size": self.memory_cache.size(),
            "redis_available": self.redis_cache is not None
        }
    
    async def close(self):
        """Close all cache connections."""
        if self.redis_cache:
            await self.redis_cache.close()


class CacheInvalidator:
    """Smart cache invalidation strategies."""
    
    def __init__(self, cache_manager: HybridCacheManager):
        self.cache_manager = cache_manager
    
    async def invalidate_category_cache(self, category_id: str):
        """Invalidate category and related caches."""
        patterns = [
            f"taxonomy:categories:{category_id}*",
            f"taxonomy:categories:root*",  # Root might include this category
            f"search:category:{category_id}*",
            f"browse:category:{category_id}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.delete_pattern(pattern)
    
    
    async def invalidate_search_cache(self, query: str):
        """Invalidate search-related caches."""
        # Hash the query for consistent key generation
        query_hash = hashlib.md5(query.encode()).hexdigest()
        patterns = [
            f"search:query:{query_hash}*",
            f"browse:search:{query_hash}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.delete_pattern(pattern)
    
    async def invalidate_policy_cache(self, policy_type: str, marketplace_id: str):
        """Invalidate policy-related caches."""
        patterns = [
            f"account:policies:{policy_type}:{marketplace_id}*",
            f"account:rate_tables:{marketplace_id}*"
        ]
        
        for pattern in patterns:
            await self.cache_manager.delete_pattern(pattern)


# TTL constants for different data types
class CacheTTL:
    """Cache TTL constants based on data volatility."""
    
    OAUTH_TOKENS = 1800  # 30 minutes
    CATEGORIES = 86400  # 24 hours
    SHIPPING_RATES = 86400  # 24 hours
    MARKET_TRENDS = 21600  # 6 hours
    SEARCH_RESULTS = 300  # 5 minutes
    BUSINESS_POLICIES = 86400  # 24 hours
    SELLER_STANDARDS = 3600  # 1 hour
    RATE_TABLES = 86400  # 24 hours


# Global cache manager instance
cache_manager: Optional[HybridCacheManager] = None


def get_cache_manager() -> Optional[HybridCacheManager]:
    """Get the global cache manager instance."""
    return cache_manager


def init_cache_manager(redis_url: Optional[str] = None) -> HybridCacheManager:
    """Initialize the global cache manager."""
    global cache_manager
    cache_manager = HybridCacheManager(redis_url=redis_url)
    return cache_manager
