# Advanced Caching Strategy for DataFlux
# Multi-level caching with Redis, application-level, and CDN integration

import asyncio
import json
import pickle
import hashlib
import time
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
import aioredis
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheLevel(Enum):
    L1 = "l1"  # Application memory cache
    L2 = "l2"  # Redis cache
    L3 = "l3"  # Database cache
    CDN = "cdn"  # CDN cache

class CacheStrategy(Enum):
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"
    READ_THROUGH = "read_through"
    CACHE_ASIDE = "cache_aside"

@dataclass
class CacheConfig:
    """Cache configuration"""
    default_ttl: int = 3600  # 1 hour
    max_size: int = 1000
    compression: bool = True
    serialize_method: str = "json"  # json, pickle
    key_prefix: str = "dataflux"
    namespace: str = "default"

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = None
    level: CacheLevel = CacheLevel.L2
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE

class CacheManager:
    """Advanced cache manager with multi-level caching"""
    
    def __init__(self, redis_url: str, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client = None
        self.memory_cache = {}  # L1 cache
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
        self.redis_url = redis_url
        
    async def init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                self.redis_url,
                decode_responses=False,  # Keep binary for pickle
                max_connections=20,
                retry_on_timeout=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _generate_key(self, key: str, namespace: str = None) -> str:
        """Generate cache key with prefix and namespace"""
        namespace = namespace or self.config.namespace
        return f"{self.config.key_prefix}:{namespace}:{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if self.config.serialize_method == "pickle":
            return pickle.dumps(value)
        elif self.config.serialize_method == "json":
            return json.dumps(value, default=str).encode('utf-8')
        else:
            return str(value).encode('utf-8')
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            if self.config.serialize_method == "pickle":
                return pickle.loads(data)
            elif self.config.serialize_method == "json":
                return json.loads(data.decode('utf-8'))
            else:
                return data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to deserialize value: {e}")
            return None
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() > entry.expires_at
    
    def _evict_lru(self):
        """Evict least recently used entry from memory cache"""
        if len(self.memory_cache) >= self.config.max_size:
            # Find LRU entry
            lru_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k].last_accessed or self.memory_cache[k].created_at
            )
            del self.memory_cache[lru_key]
            self.cache_stats["evictions"] += 1
            logger.info(f"Evicted LRU entry: {lru_key}")
    
    async def get(self, key: str, namespace: str = None) -> Optional[Any]:
        """Get value from cache (L1 -> L2 -> L3)"""
        cache_key = self._generate_key(key, namespace)
        
        # Try L1 cache (memory) first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not self._is_expired(entry):
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self.cache_stats["hits"] += 1
                logger.debug(f"L1 cache hit: {key}")
                return entry.value
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]
        
        # Try L2 cache (Redis)
        if self.redis_client:
            try:
                data = await self.redis_client.get(cache_key)
                if data:
                    value = self._deserialize_value(data)
                    if value is not None:
                        # Store in L1 cache
                        self._evict_lru()
                        entry = CacheEntry(
                            key=cache_key,
                            value=value,
                            created_at=datetime.now(),
                            expires_at=datetime.now() + timedelta(seconds=self.config.default_ttl),
                            level=CacheLevel.L2
                        )
                        self.memory_cache[cache_key] = entry
                        self.cache_stats["hits"] += 1
                        logger.debug(f"L2 cache hit: {key}")
                        return value
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        self.cache_stats["misses"] += 1
        logger.debug(f"Cache miss: {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None, 
                  namespace: str = None, strategy: CacheStrategy = None) -> bool:
        """Set value in cache"""
        cache_key = self._generate_key(key, namespace)
        ttl = ttl or self.config.default_ttl
        strategy = strategy or CacheStrategy.CACHE_ASIDE
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            strategy=strategy
        )
        
        # Store in L1 cache (memory)
        self._evict_lru()
        self.memory_cache[cache_key] = entry
        
        # Store in L2 cache (Redis) based on strategy
        if self.redis_client and strategy in [CacheStrategy.WRITE_THROUGH, CacheStrategy.CACHE_ASIDE]:
            try:
                data = self._serialize_value(value)
                await self.redis_client.setex(cache_key, ttl, data)
                logger.debug(f"Stored in L2 cache: {key}")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        self.cache_stats["sets"] += 1
        logger.debug(f"Cache set: {key}")
        return True
    
    async def delete(self, key: str, namespace: str = None) -> bool:
        """Delete value from cache"""
        cache_key = self._generate_key(key, namespace)
        
        # Remove from L1 cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        # Remove from L2 cache
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                logger.debug(f"Deleted from L2 cache: {key}")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        self.cache_stats["deletes"] += 1
        logger.debug(f"Cache delete: {key}")
        return True
    
    async def exists(self, key: str, namespace: str = None) -> bool:
        """Check if key exists in cache"""
        cache_key = self._generate_key(key, namespace)
        
        # Check L1 cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not self._is_expired(entry):
                return True
            else:
                del self.memory_cache[cache_key]
        
        # Check L2 cache
        if self.redis_client:
            try:
                return await self.redis_client.exists(cache_key) > 0
            except Exception as e:
                logger.error(f"Redis exists error: {e}")
        
        return False
    
    async def clear(self, namespace: str = None) -> bool:
        """Clear cache namespace"""
        if namespace:
            pattern = f"{self.config.key_prefix}:{namespace}:*"
        else:
            pattern = f"{self.config.key_prefix}:*"
        
        # Clear L1 cache
        keys_to_remove = [k for k in self.memory_cache.keys() if k.startswith(pattern)]
        for key in keys_to_remove:
            del self.memory_cache[key]
        
        # Clear L2 cache
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                logger.info(f"Cleared cache namespace: {namespace or 'all'}")
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            "hit_rate": hit_rate,
            "memory_cache_size": len(self.memory_cache),
            "memory_cache_max": self.config.max_size,
            "memory_usage_percent": (len(self.memory_cache) / self.config.max_size * 100)
        }
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

class QueryCache:
    """Specialized cache for database queries"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.query_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "query_executions": 0
        }
    
    def _generate_query_key(self, query: str, params: tuple = None) -> str:
        """Generate cache key for query"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if params:
            params_hash = hashlib.md5(str(params).encode()).hexdigest()
            return f"query:{query_hash}:{params_hash}"
        return f"query:{query_hash}"
    
    async def get_query_result(self, query: str, params: tuple = None) -> Optional[Any]:
        """Get cached query result"""
        key = self._generate_query_key(query, params)
        result = await self.cache_manager.get(key, "queries")
        
        if result is not None:
            self.query_stats["cache_hits"] += 1
            logger.debug(f"Query cache hit: {query[:50]}...")
        else:
            self.query_stats["cache_misses"] += 1
            logger.debug(f"Query cache miss: {query[:50]}...")
        
        return result
    
    async def set_query_result(self, query: str, result: Any, ttl: int = 3600, 
                              params: tuple = None) -> bool:
        """Cache query result"""
        key = self._generate_query_key(query, params)
        success = await self.cache_manager.set(key, result, ttl, "queries")
        
        if success:
            self.query_stats["query_executions"] += 1
            logger.debug(f"Cached query result: {query[:50]}...")
        
        return success
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query cache statistics"""
        total_queries = self.query_stats["cache_hits"] + self.query_stats["cache_misses"]
        hit_rate = (self.query_stats["cache_hits"] / total_queries * 100) if total_queries > 0 else 0
        
        return {
            **self.query_stats,
            "hit_rate": hit_rate
        }

class AssetCache:
    """Specialized cache for asset operations"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def get_asset_metadata(self, asset_id: str) -> Optional[Dict]:
        """Get cached asset metadata"""
        return await self.cache_manager.get(f"asset_meta:{asset_id}", "assets")
    
    async def set_asset_metadata(self, asset_id: str, metadata: Dict, ttl: int = 7200) -> bool:
        """Cache asset metadata"""
        return await self.cache_manager.set(f"asset_meta:{asset_id}", metadata, ttl, "assets")
    
    async def get_asset_thumbnail(self, asset_id: str) -> Optional[bytes]:
        """Get cached asset thumbnail"""
        return await self.cache_manager.get(f"asset_thumb:{asset_id}", "assets")
    
    async def set_asset_thumbnail(self, asset_id: str, thumbnail: bytes, ttl: int = 86400) -> bool:
        """Cache asset thumbnail"""
        return await self.cache_manager.set(f"asset_thumb:{asset_id}", thumbnail, ttl, "assets")
    
    async def get_asset_embeddings(self, asset_id: str) -> Optional[List]:
        """Get cached asset embeddings"""
        return await self.cache_manager.get(f"asset_embeddings:{asset_id}", "assets")
    
    async def set_asset_embeddings(self, asset_id: str, embeddings: List, ttl: int = 3600) -> bool:
        """Cache asset embeddings"""
        return await self.cache_manager.set(f"asset_embeddings:{asset_id}", embeddings, ttl, "assets")
    
    async def invalidate_asset(self, asset_id: str):
        """Invalidate all asset-related cache entries"""
        patterns = [
            f"asset_meta:{asset_id}",
            f"asset_thumb:{asset_id}",
            f"asset_embeddings:{asset_id}"
        ]
        
        for pattern in patterns:
            await self.cache_manager.delete(pattern, "assets")

class SearchCache:
    """Specialized cache for search operations"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def _generate_search_key(self, query: str, filters: Dict = None, limit: int = None) -> str:
        """Generate cache key for search query"""
        search_data = {
            "query": query,
            "filters": filters or {},
            "limit": limit
        }
        search_hash = hashlib.md5(json.dumps(search_data, sort_keys=True).encode()).hexdigest()
        return f"search:{search_hash}"
    
    async def get_search_results(self, query: str, filters: Dict = None, 
                                limit: int = None) -> Optional[List]:
        """Get cached search results"""
        key = self._generate_search_key(query, filters, limit)
        return await self.cache_manager.get(key, "search")
    
    async def set_search_results(self, query: str, results: List, ttl: int = 1800,
                                filters: Dict = None, limit: int = None) -> bool:
        """Cache search results"""
        key = self._generate_search_key(query, filters, limit)
        return await self.cache_manager.set(key, results, ttl, "search")
    
    async def invalidate_search_cache(self):
        """Invalidate all search cache entries"""
        await self.cache_manager.clear("search")

# Global cache manager instance
cache_manager = None
query_cache = None
asset_cache = None
search_cache = None

async def init_caching(redis_url: str = "redis://localhost:2002"):
    """Initialize caching system"""
    global cache_manager, query_cache, asset_cache, search_cache
    
    config = CacheConfig(
        default_ttl=3600,
        max_size=1000,
        compression=True,
        serialize_method="pickle",
        key_prefix="dataflux",
        namespace="default"
    )
    
    cache_manager = CacheManager(redis_url, config)
    await cache_manager.init_redis()
    
    query_cache = QueryCache(cache_manager)
    asset_cache = AssetCache(cache_manager)
    search_cache = SearchCache(cache_manager)
    
    logger.info("Caching system initialized")

async def close_caching():
    """Close caching system"""
    global cache_manager
    if cache_manager:
        await cache_manager.close()

# Decorator for automatic caching
def cached(ttl: int = 3600, namespace: str = "default"):
    """Decorator for automatic function result caching"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            if cache_manager:
                result = await cache_manager.get(cache_key, namespace)
                if result is not None:
                    return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if cache_manager:
                await cache_manager.set(cache_key, result, ttl, namespace)
            
            return result
        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    async def main():
        await init_caching()
        
        # Test basic caching
        await cache_manager.set("test_key", {"data": "test_value"}, 60)
        result = await cache_manager.get("test_key")
        print(f"Cached result: {result}")
        
        # Test query caching
        query_result = await query_cache.get_query_result("SELECT * FROM assets LIMIT 10")
        if query_result is None:
            # Simulate database query
            query_result = [{"id": 1, "name": "test_asset"}]
            await query_cache.set_query_result("SELECT * FROM assets LIMIT 10", query_result)
        
        # Test asset caching
        await asset_cache.set_asset_metadata("asset_123", {"name": "test", "size": 1024})
        metadata = await asset_cache.get_asset_metadata("asset_123")
        print(f"Asset metadata: {metadata}")
        
        # Print statistics
        print(f"Cache stats: {cache_manager.get_stats()}")
        print(f"Query cache stats: {query_cache.get_query_stats()}")
        
        await close_caching()
    
    asyncio.run(main())
