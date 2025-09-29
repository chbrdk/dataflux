# Connection Pooling Configuration for DataFlux
# Optimized connection pooling for PostgreSQL, Redis, and other services

import asyncio
import asyncpg
import aioredis
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import os
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PoolType(Enum):
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    KAFKA = "kafka"
    MINIO = "minio"

@dataclass
class PoolConfig:
    """Connection pool configuration"""
    min_connections: int = 5
    max_connections: int = 20
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0  # 5 minutes
    command_timeout: float = 60.0
    server_settings: Dict[str, str] = None

@dataclass
class RedisPoolConfig:
    """Redis connection pool configuration"""
    max_connections: int = 20
    retry_on_timeout: bool = True
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[int, int] = None
    health_check_interval: int = 30

class ConnectionPoolManager:
    """Advanced connection pool manager for DataFlux services"""
    
    def __init__(self):
        self.pools = {}
        self.configs = {}
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "connection_errors": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
    
    async def init_postgresql_pool(self, 
                                 host: str = "localhost",
                                 port: int = 2001,
                                 user: str = "dataflux_user",
                                 password: str = "dataflux_pass",
                                 database: str = "dataflux",
                                 config: PoolConfig = None) -> asyncpg.Pool:
        """Initialize PostgreSQL connection pool"""
        config = config or PoolConfig()
        
        try:
            pool = await asyncpg.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                min_size=config.min_connections,
                max_size=config.max_connections,
                max_queries=config.max_queries,
                max_inactive_connection_lifetime=config.max_inactive_connection_lifetime,
                command_timeout=config.command_timeout,
                server_settings=config.server_settings or {
                    'application_name': 'dataflux',
                    'jit': 'off',  # Disable JIT for better connection performance
                    'shared_preload_libraries': 'pg_stat_statements'
                }
            )
            
            self.pools[PoolType.POSTGRESQL] = pool
            self.configs[PoolType.POSTGRESQL] = config
            
            # Test connection
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            logger.info(f"PostgreSQL pool initialized: {config.min_connections}-{config.max_connections} connections")
            return pool
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            self.stats["connection_errors"] += 1
            raise
    
    async def init_redis_pool(self,
                            url: str = "redis://localhost:2002",
                            config: RedisPoolConfig = None) -> aioredis.ConnectionPool:
        """Initialize Redis connection pool"""
        config = config or RedisPoolConfig()
        
        try:
            pool = aioredis.ConnectionPool.from_url(
                url,
                max_connections=config.max_connections,
                retry_on_timeout=config.retry_on_timeout,
                socket_keepalive=config.socket_keepalive,
                socket_keepalive_options=config.socket_keepalive_options or {
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5   # TCP_KEEPCNT
                },
                health_check_interval=config.health_check_interval,
                decode_responses=True
            )
            
            redis_client = aioredis.Redis(connection_pool=pool)
            
            # Test connection
            await redis_client.ping()
            
            self.pools[PoolType.REDIS] = redis_client
            self.configs[PoolType.REDIS] = config
            
            logger.info(f"Redis pool initialized: {config.max_connections} connections")
            return redis_client
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            self.stats["connection_errors"] += 1
            raise
    
    @asynccontextmanager
    async def get_postgresql_connection(self):
        """Get PostgreSQL connection from pool"""
        if PoolType.POSTGRESQL not in self.pools:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        pool = self.pools[PoolType.POSTGRESQL]
        
        try:
            async with pool.acquire() as conn:
                self.stats["pool_hits"] += 1
                self.stats["active_connections"] += 1
                yield conn
        except Exception as e:
            self.stats["pool_misses"] += 1
            self.stats["connection_errors"] += 1
            logger.error(f"Failed to get PostgreSQL connection: {e}")
            raise
        finally:
            self.stats["active_connections"] = max(0, self.stats["active_connections"] - 1)
    
    async def get_redis_connection(self):
        """Get Redis connection from pool"""
        if PoolType.REDIS not in self.pools:
            raise RuntimeError("Redis pool not initialized")
        
        return self.pools[PoolType.REDIS]
    
    async def execute_query(self, query: str, *args, **kwargs) -> Any:
        """Execute PostgreSQL query with connection pooling"""
        async with self.get_postgresql_connection() as conn:
            if query.strip().upper().startswith('SELECT'):
                return await conn.fetch(query, *args)
            else:
                return await conn.execute(query, *args)
    
    async def execute_transaction(self, queries: list) -> Any:
        """Execute multiple queries in a transaction"""
        async with self.get_postgresql_connection() as conn:
            async with conn.transaction():
                results = []
                for query, args in queries:
                    if query.strip().upper().startswith('SELECT'):
                        result = await conn.fetch(query, *args)
                    else:
                        result = await conn.execute(query, *args)
                    results.append(result)
                return results
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = self.stats.copy()
        
        # Add PostgreSQL pool stats
        if PoolType.POSTGRESQL in self.pools:
            pool = self.pools[PoolType.POSTGRESQL]
            stats.update({
                "postgresql_pool_size": pool.get_size(),
                "postgresql_idle_connections": pool.get_idle_size(),
                "postgresql_max_size": pool.get_max_size(),
                "postgresql_min_size": pool.get_min_size()
            })
        
        # Add Redis pool stats
        if PoolType.REDIS in self.pools:
            redis_client = self.pools[PoolType.REDIS]
            stats.update({
                "redis_pool_size": redis_client.connection_pool.max_connections,
                "redis_active_connections": len(redis_client.connection_pool._available_connections)
            })
        
        return stats
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connection pools"""
        health_status = {}
        
        # Check PostgreSQL
        if PoolType.POSTGRESQL in self.pools:
            try:
                async with self.get_postgresql_connection() as conn:
                    await conn.execute("SELECT 1")
                health_status["postgresql"] = True
            except Exception as e:
                logger.error(f"PostgreSQL health check failed: {e}")
                health_status["postgresql"] = False
        
        # Check Redis
        if PoolType.REDIS in self.pools:
            try:
                redis_client = self.pools[PoolType.REDIS]
                await redis_client.ping()
                health_status["redis"] = True
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                health_status["redis"] = False
        
        return health_status
    
    async def close_all_pools(self):
        """Close all connection pools"""
        for pool_type, pool in self.pools.items():
            try:
                if pool_type == PoolType.POSTGRESQL:
                    await pool.close()
                elif pool_type == PoolType.REDIS:
                    await pool.close()
                logger.info(f"Closed {pool_type.value} pool")
            except Exception as e:
                logger.error(f"Error closing {pool_type.value} pool: {e}")
        
        self.pools.clear()
        logger.info("All connection pools closed")

class QueryOptimizer:
    """Query optimization utilities"""
    
    def __init__(self, pool_manager: ConnectionPoolManager):
        self.pool_manager = pool_manager
        self.query_cache = {}
        self.query_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "slow_queries": 0,
            "query_errors": 0
        }
    
    async def execute_optimized_query(self, query: str, *args, **kwargs) -> Any:
        """Execute query with optimization"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check if query is cached
            query_hash = hash(query + str(args))
            if query_hash in self.query_cache:
                self.query_stats["cache_hits"] += 1
                logger.debug(f"Query cache hit: {query[:50]}...")
                return self.query_cache[query_hash]
            
            # Execute query
            result = await self.pool_manager.execute_query(query, *args, **kwargs)
            
            # Cache SELECT queries
            if query.strip().upper().startswith('SELECT') and len(self.query_cache) < 1000:
                self.query_cache[query_hash] = result
            
            # Track slow queries
            execution_time = asyncio.get_event_loop().time() - start_time
            if execution_time > 1.0:  # Queries taking more than 1 second
                self.query_stats["slow_queries"] += 1
                logger.warning(f"Slow query detected ({execution_time:.2f}s): {query[:100]}...")
            
            self.query_stats["total_queries"] += 1
            return result
            
        except Exception as e:
            self.query_stats["query_errors"] += 1
            logger.error(f"Query execution error: {e}")
            raise
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        total_queries = self.query_stats["total_queries"]
        cache_hit_rate = (self.query_stats["cache_hits"] / total_queries * 100) if total_queries > 0 else 0
        
        return {
            **self.query_stats,
            "cache_hit_rate": cache_hit_rate,
            "cached_queries": len(self.query_cache)
        }
    
    def clear_query_cache(self):
        """Clear query cache"""
        self.query_cache.clear()
        logger.info("Query cache cleared")

class DatabaseMonitor:
    """Database performance monitoring"""
    
    def __init__(self, pool_manager: ConnectionPoolManager):
        self.pool_manager = pool_manager
        self.monitoring_active = False
        self.monitoring_task = None
    
    async def start_monitoring(self, interval: int = 60):
        """Start database monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"Database monitoring started (interval: {interval}s)")
    
    async def stop_monitoring(self):
        """Stop database monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Database monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Monitoring loop"""
        while self.monitoring_active:
            try:
                await self._collect_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_metrics(self):
        """Collect database metrics"""
        try:
            # Get pool statistics
            pool_stats = self.pool_manager.get_pool_stats()
            
            # Get health status
            health_status = await self.pool_manager.health_check()
            
            # Log metrics
            logger.info(f"Pool stats: {pool_stats}")
            logger.info(f"Health status: {health_status}")
            
            # Check for issues
            if not health_status.get("postgresql", True):
                logger.warning("PostgreSQL connection issues detected")
            
            if not health_status.get("redis", True):
                logger.warning("Redis connection issues detected")
            
            # Check pool utilization
            if pool_stats.get("postgresql_pool_size", 0) > pool_stats.get("postgresql_max_size", 0) * 0.8:
                logger.warning("PostgreSQL pool utilization high")
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")

# Global pool manager instance
pool_manager = ConnectionPoolManager()
query_optimizer = QueryOptimizer(pool_manager)
db_monitor = DatabaseMonitor(pool_manager)

async def init_connection_pools():
    """Initialize all connection pools"""
    # PostgreSQL pool
    await pool_manager.init_postgresql_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "2001")),
        user=os.getenv("POSTGRES_USER", "dataflux_user"),
        password=os.getenv("POSTGRES_PASSWORD", "dataflux_pass"),
        database=os.getenv("POSTGRES_DB", "dataflux"),
        config=PoolConfig(
            min_connections=5,
            max_connections=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300.0,
            command_timeout=60.0
        )
    )
    
    # Redis pool
    await pool_manager.init_redis_pool(
        url=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '2002')}",
        config=RedisPoolConfig(
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            health_check_interval=30
        )
    )
    
    # Start monitoring
    await db_monitor.start_monitoring(interval=60)
    
    logger.info("All connection pools initialized")

async def close_connection_pools():
    """Close all connection pools"""
    await db_monitor.stop_monitoring()
    await pool_manager.close_all_pools()
    logger.info("All connection pools closed")

# Example usage
if __name__ == "__main__":
    async def main():
        await init_connection_pools()
        
        # Test PostgreSQL connection
        async with pool_manager.get_postgresql_connection() as conn:
            result = await conn.fetch("SELECT version()")
            print(f"PostgreSQL version: {result[0]['version']}")
        
        # Test Redis connection
        redis_client = await pool_manager.get_redis_connection()
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        print(f"Redis test: {value}")
        
        # Test optimized query
        result = await query_optimizer.execute_optimized_query(
            "SELECT COUNT(*) FROM assets WHERE is_active = true"
        )
        print(f"Asset count: {result[0]['count']}")
        
        # Print statistics
        print(f"Pool stats: {pool_manager.get_pool_stats()}")
        print(f"Query stats: {query_optimizer.get_query_stats()}")
        
        await close_connection_pools()
    
    asyncio.run(main())
