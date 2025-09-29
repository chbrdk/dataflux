# Performance Monitoring Dashboard for DataFlux
# Real-time performance monitoring and alerting

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import psutil
import asyncpg
import aioredis
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = None
    metric_type: MetricType = MetricType.GAUGE

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    threshold: float
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    duration: int  # seconds
    severity: str  # 'critical', 'warning', 'info'

@dataclass
class Alert:
    """Alert data structure"""
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: str
    timestamp: datetime
    message: str

class PerformanceMonitor:
    """Advanced performance monitoring system"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.alert_rules = []
        self.monitoring_active = False
        self.monitoring_task = None
        self.prometheus_metrics = {}
        self.db_pool = None
        self.redis_client = None
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Load alert rules
        self._load_default_alert_rules()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        # System metrics
        self.prometheus_metrics['cpu_usage'] = Gauge('dataflux_cpu_usage_percent', 'CPU usage percentage')
        self.prometheus_metrics['memory_usage'] = Gauge('dataflux_memory_usage_bytes', 'Memory usage in bytes')
        self.prometheus_metrics['disk_usage'] = Gauge('dataflux_disk_usage_percent', 'Disk usage percentage')
        
        # Database metrics
        self.prometheus_metrics['db_connections'] = Gauge('dataflux_db_connections', 'Database connections')
        self.prometheus_metrics['db_query_duration'] = Histogram('dataflux_db_query_duration_seconds', 'Database query duration')
        self.prometheus_metrics['db_query_count'] = Counter('dataflux_db_queries_total', 'Total database queries')
        
        # Redis metrics
        self.prometheus_metrics['redis_connections'] = Gauge('dataflux_redis_connections', 'Redis connections')
        self.prometheus_metrics['redis_operations'] = Counter('dataflux_redis_operations_total', 'Total Redis operations')
        
        # Service metrics
        self.prometheus_metrics['service_requests'] = Counter('dataflux_service_requests_total', 'Total service requests')
        self.prometheus_metrics['service_response_time'] = Histogram('dataflux_service_response_time_seconds', 'Service response time')
        self.prometheus_metrics['service_errors'] = Counter('dataflux_service_errors_total', 'Total service errors')
        
        # Cache metrics
        self.prometheus_metrics['cache_hits'] = Counter('dataflux_cache_hits_total', 'Total cache hits')
        self.prometheus_metrics['cache_misses'] = Counter('dataflux_cache_misses_total', 'Total cache misses')
        self.prometheus_metrics['cache_size'] = Gauge('dataflux_cache_size_bytes', 'Cache size in bytes')
    
    def _load_default_alert_rules(self):
        """Load default alert rules"""
        self.alert_rules = [
            AlertRule("high_cpu_usage", "cpu_usage", 80.0, ">", 300, "warning"),
            AlertRule("critical_cpu_usage", "cpu_usage", 95.0, ">", 60, "critical"),
            AlertRule("high_memory_usage", "memory_usage", 80.0, ">", 300, "warning"),
            AlertRule("critical_memory_usage", "memory_usage", 95.0, ">", 60, "critical"),
            AlertRule("high_disk_usage", "disk_usage", 85.0, ">", 300, "warning"),
            AlertRule("critical_disk_usage", "disk_usage", 95.0, ">", 60, "critical"),
            AlertRule("high_db_connections", "db_connections", 15.0, ">", 300, "warning"),
            AlertRule("critical_db_connections", "db_connections", 18.0, ">", 60, "critical"),
            AlertRule("slow_query", "db_query_duration", 5.0, ">", 60, "warning"),
            AlertRule("high_error_rate", "service_error_rate", 5.0, ">", 300, "warning"),
        ]
    
    async def init_connections(self):
        """Initialize database and Redis connections"""
        try:
            # PostgreSQL connection
            self.db_pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "2001")),
                user=os.getenv("POSTGRES_USER", "dataflux_user"),
                password=os.getenv("POSTGRES_PASSWORD", "dataflux_pass"),
                database=os.getenv("POSTGRES_DB", "dataflux"),
                min_size=2,
                max_size=5
            )
            
            # Redis connection
            self.redis_client = aioredis.from_url(
                f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '2002')}",
                decode_responses=True
            )
            
            logger.info("Performance monitor connections initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
            raise
    
    async def collect_system_metrics(self) -> Dict[str, float]:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            metrics = {
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'memory_used_bytes': memory_used,
                'disk_usage': disk_percent,
                'disk_used_bytes': disk.used,
                'network_bytes_sent': network_bytes_sent,
                'network_bytes_recv': network_bytes_recv
            }
            
            # Update Prometheus metrics
            self.prometheus_metrics['cpu_usage'].set(cpu_percent)
            self.prometheus_metrics['memory_usage'].set(memory_used)
            self.prometheus_metrics['disk_usage'].set(disk_percent)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    async def collect_database_metrics(self) -> Dict[str, float]:
        """Collect database performance metrics"""
        if not self.db_pool:
            return {}
        
        try:
            async with self.db_pool.acquire() as conn:
                # Connection count
                conn_count = await conn.fetchval("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                
                # Query performance
                slow_queries = await conn.fetchval("""
                    SELECT COUNT(*) FROM pg_stat_statements 
                    WHERE mean_exec_time > 1000
                """)
                
                # Cache hit ratio
                cache_hit_ratio = await conn.fetchval("""
                    SELECT 
                        round(100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2) as cache_hit_ratio
                    FROM pg_stat_database
                """)
                
                # Database size
                db_size = await conn.fetchval("SELECT pg_database_size(current_database())")
                
                metrics = {
                    'db_connections': float(conn_count),
                    'slow_queries': float(slow_queries),
                    'cache_hit_ratio': float(cache_hit_ratio or 0),
                    'db_size_bytes': float(db_size)
                }
                
                # Update Prometheus metrics
                self.prometheus_metrics['db_connections'].set(conn_count)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return {}
    
    async def collect_redis_metrics(self) -> Dict[str, float]:
        """Collect Redis performance metrics"""
        if not self.redis_client:
            return {}
        
        try:
            # Redis info
            info = await self.redis_client.info()
            
            # Connection count
            connected_clients = info.get('connected_clients', 0)
            
            # Memory usage
            used_memory = info.get('used_memory', 0)
            used_memory_percent = info.get('used_memory_percentage', 0)
            
            # Operations
            total_commands_processed = info.get('total_commands_processed', 0)
            
            # Hit ratio
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)
            hit_ratio = (keyspace_hits / (keyspace_hits + keyspace_misses) * 100) if (keyspace_hits + keyspace_misses) > 0 else 0
            
            metrics = {
                'redis_connections': float(connected_clients),
                'redis_memory_used': float(used_memory),
                'redis_memory_percent': float(used_memory_percent),
                'redis_operations': float(total_commands_processed),
                'redis_hit_ratio': float(hit_ratio)
            }
            
            # Update Prometheus metrics
            self.prometheus_metrics['redis_connections'].set(connected_clients)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Redis metrics: {e}")
            return {}
    
    async def collect_service_metrics(self) -> Dict[str, float]:
        """Collect service performance metrics"""
        try:
            # This would typically collect metrics from each service
            # For now, we'll simulate some metrics
            
            metrics = {
                'ingestion_service_requests': 0,
                'query_service_requests': 0,
                'analysis_service_requests': 0,
                'mcp_server_requests': 0,
                'web_ui_requests': 0,
                'api_gateway_requests': 0
            }
            
            # Update Prometheus metrics
            self.prometheus_metrics['service_requests'].inc()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect service metrics: {e}")
            return {}
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all performance metrics"""
        all_metrics = {}
        
        # Collect system metrics
        system_metrics = await self.collect_system_metrics()
        all_metrics.update(system_metrics)
        
        # Collect database metrics
        db_metrics = await self.collect_database_metrics()
        all_metrics.update(db_metrics)
        
        # Collect Redis metrics
        redis_metrics = await self.collect_redis_metrics()
        all_metrics.update(redis_metrics)
        
        # Collect service metrics
        service_metrics = await self.collect_service_metrics()
        all_metrics.update(service_metrics)
        
        # Add timestamp
        all_metrics['timestamp'] = datetime.now().isoformat()
        
        return all_metrics
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check metrics against alert rules"""
        new_alerts = []
        
        for rule in self.alert_rules:
            if rule.metric_name not in metrics:
                continue
            
            current_value = metrics[rule.metric_name]
            threshold = rule.threshold
            
            # Check if alert condition is met
            alert_triggered = False
            if rule.operator == '>':
                alert_triggered = current_value > threshold
            elif rule.operator == '<':
                alert_triggered = current_value < threshold
            elif rule.operator == '>=':
                alert_triggered = current_value >= threshold
            elif rule.operator == '<=':
                alert_triggered = current_value <= threshold
            elif rule.operator == '==':
                alert_triggered = current_value == threshold
            elif rule.operator == '!=':
                alert_triggered = current_value != threshold
            
            if alert_triggered:
                alert = Alert(
                    rule_name=rule.name,
                    metric_name=rule.metric_name,
                    current_value=current_value,
                    threshold=threshold,
                    severity=rule.severity,
                    timestamp=datetime.now(),
                    message=f"{rule.name}: {rule.metric_name} is {current_value} (threshold: {threshold})"
                )
                new_alerts.append(alert)
                self.alerts.append(alert)
                
                logger.warning(f"Alert triggered: {alert.message}")
        
        return new_alerts
    
    async def store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in database and Redis"""
        try:
            # Store in Redis for real-time access
            if self.redis_client:
                await self.redis_client.setex(
                    "performance_metrics:latest",
                    300,  # 5 minutes TTL
                    json.dumps(metrics)
                )
                
                # Store historical data
                timestamp = int(time.time())
                await self.redis_client.zadd(
                    "performance_metrics:history",
                    {json.dumps(metrics): timestamp}
                )
                
                # Keep only last 24 hours of data
                cutoff_time = timestamp - (24 * 60 * 60)
                await self.redis_client.zremrangebyscore(
                    "performance_metrics:history",
                    0,
                    cutoff_time
                )
            
            # Store in database for long-term storage
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO performance_metrics (metric_name, metric_value, timestamp, labels)
                        VALUES ($1, $2, $3, $4)
                    """, "system_metrics", json.dumps(metrics), datetime.now(), {})
                    
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    async def start_monitoring(self, interval: int = 60):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"Performance monitoring started (interval: {interval}s)")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = await self.collect_all_metrics()
                
                # Check alerts
                new_alerts = self.check_alerts(metrics)
                
                # Store metrics
                await self.store_metrics(metrics)
                
                # Log summary
                logger.info(f"Collected {len(metrics)} metrics, {len(new_alerts)} new alerts")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval)
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get latest metrics"""
        return self.metrics
    
    def get_alerts(self, severity: str = None) -> List[Alert]:
        """Get alerts, optionally filtered by severity"""
        if severity:
            return [alert for alert in self.alerts if alert.severity == severity]
        return self.alerts
    
    def get_alert_rules(self) -> List[AlertRule]:
        """Get alert rules"""
        return self.alert_rules
    
    def add_alert_rule(self, rule: AlertRule):
        """Add new alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove alert rule"""
        self.alert_rules = [rule for rule in self.alert_rules if rule.name != rule_name]
        logger.info(f"Removed alert rule: {rule_name}")
    
    async def close(self):
        """Close connections"""
        await self.stop_monitoring()
        
        if self.db_pool:
            await self.db_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Performance monitor closed")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

async def init_performance_monitoring():
    """Initialize performance monitoring"""
    await performance_monitor.init_connections()
    await performance_monitor.start_monitoring(interval=60)
    
    # Start Prometheus metrics server
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

async def close_performance_monitoring():
    """Close performance monitoring"""
    await performance_monitor.close()

# Example usage
if __name__ == "__main__":
    async def main():
        await init_performance_monitoring()
        
        # Run for 5 minutes
        await asyncio.sleep(300)
        
        # Print latest metrics
        metrics = performance_monitor.get_latest_metrics()
        print(f"Latest metrics: {metrics}")
        
        # Print alerts
        alerts = performance_monitor.get_alerts()
        print(f"Active alerts: {len(alerts)}")
        for alert in alerts:
            print(f"  - {alert.message}")
        
        await close_performance_monitoring()
    
    asyncio.run(main())
