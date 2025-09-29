"""
DataFlux Ingestion Service - Prometheus Metrics
Enhanced metrics collection for monitoring
"""

import time
import logging
from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IngestionMetrics:
    """Prometheus metrics for Ingestion Service"""
    
    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            'dataflux_ingestion_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'dataflux_ingestion_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # File upload metrics
        self.file_uploads = Counter(
            'dataflux_ingestion_file_uploads_total',
            'Total number of file uploads',
            ['mime_type', 'status']
        )
        
        self.file_size = Histogram(
            'dataflux_ingestion_file_size_bytes',
            'File size in bytes',
            ['mime_type'],
            buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824]
        )
        
        self.upload_duration = Histogram(
            'dataflux_ingestion_upload_duration_seconds',
            'File upload duration in seconds',
            ['mime_type'],
            buckets=[1, 5, 10, 30, 60, 300]
        )
        
        # Processing metrics
        self.processing_queue_size = Gauge(
            'dataflux_ingestion_processing_queue_size',
            'Number of files in processing queue'
        )
        
        self.processing_duration = Histogram(
            'dataflux_ingestion_processing_duration_seconds',
            'File processing duration in seconds',
            ['mime_type', 'status'],
            buckets=[1, 5, 10, 30, 60, 300, 600]
        )
        
        self.processing_failed = Counter(
            'dataflux_ingestion_processing_failed_total',
            'Total number of failed processing jobs',
            ['mime_type', 'error_type']
        )
        
        # Storage metrics
        self.storage_operations = Counter(
            'dataflux_ingestion_storage_operations_total',
            'Total number of storage operations',
            ['operation', 'status']
        )
        
        self.storage_duration = Histogram(
            'dataflux_ingestion_storage_duration_seconds',
            'Storage operation duration in seconds',
            ['operation'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # Database metrics
        self.database_operations = Counter(
            'dataflux_ingestion_database_operations_total',
            'Total number of database operations',
            ['operation', 'status']
        )
        
        self.database_duration = Histogram(
            'dataflux_ingestion_database_duration_seconds',
            'Database operation duration in seconds',
            ['operation'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0]
        )
        
        # Kafka metrics
        self.kafka_messages_sent = Counter(
            'dataflux_ingestion_kafka_messages_sent_total',
            'Total number of Kafka messages sent',
            ['topic', 'status']
        )
        
        self.kafka_send_duration = Histogram(
            'dataflux_ingestion_kafka_send_duration_seconds',
            'Kafka message send duration in seconds',
            ['topic'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0]
        )
        
        # System metrics
        self.active_connections = Gauge(
            'dataflux_ingestion_active_connections',
            'Number of active connections'
        )
        
        self.memory_usage = Gauge(
            'dataflux_ingestion_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.cpu_usage = Gauge(
            'dataflux_ingestion_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        # Business metrics
        self.duplicate_files = Counter(
            'dataflux_ingestion_duplicate_files_total',
            'Total number of duplicate files detected',
            ['mime_type']
        )
        
        self.collection_uploads = Counter(
            'dataflux_ingestion_collection_uploads_total',
            'Total number of uploads per collection',
            ['collection_id']
        )
        
        # Error metrics
        self.error_count = Counter(
            'dataflux_ingestion_errors_total',
            'Total number of errors',
            ['error_type', 'component']
        )
        
        # Start metrics server
        try:
            start_http_server(8002)  # Use different port for metrics
            logger.info("✅ Prometheus metrics server started on port 8002")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start metrics server: {e}")
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        self.request_count.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_file_upload(self, mime_type: str, file_size: int, duration: float, status: str):
        """Record file upload metrics"""
        self.file_uploads.labels(mime_type=mime_type, status=status).inc()
        self.file_size.labels(mime_type=mime_type).observe(file_size)
        self.upload_duration.labels(mime_type=mime_type).observe(duration)
    
    def record_processing(self, mime_type: str, duration: float, status: str):
        """Record processing metrics"""
        self.processing_duration.labels(mime_type=mime_type, status=status).observe(duration)
        if status == "failed":
            self.processing_failed.labels(mime_type=mime_type, error_type="processing").inc()
    
    def record_storage_operation(self, operation: str, duration: float, status: str):
        """Record storage operation metrics"""
        self.storage_operations.labels(operation=operation, status=status).inc()
        self.storage_duration.labels(operation=operation).observe(duration)
    
    def record_database_operation(self, operation: str, duration: float, status: str):
        """Record database operation metrics"""
        self.database_operations.labels(operation=operation, status=status).inc()
        self.database_duration.labels(operation=operation).observe(duration)
    
    def record_kafka_message(self, topic: str, duration: float, status: str):
        """Record Kafka message metrics"""
        self.kafka_messages_sent.labels(topic=topic, status=status).inc()
        self.kafka_send_duration.labels(topic=topic).observe(duration)
    
    def record_duplicate_file(self, mime_type: str):
        """Record duplicate file detection"""
        self.duplicate_files.labels(mime_type=mime_type).inc()
    
    def record_collection_upload(self, collection_id: str):
        """Record collection upload"""
        self.collection_uploads.labels(collection_id=collection_id).inc()
    
    def record_error(self, error_type: str, component: str):
        """Record error metrics"""
        self.error_count.labels(error_type=error_type, component=component).inc()
    
    def update_queue_size(self, size: int):
        """Update processing queue size"""
        self.processing_queue_size.set(size)
    
    def update_active_connections(self, count: int):
        """Update active connections count"""
        self.active_connections.set(count)
    
    def update_system_metrics(self, memory_bytes: int, cpu_percent: float):
        """Update system metrics"""
        self.memory_usage.set(memory_bytes)
        self.cpu_usage.set(cpu_percent)

# Global metrics instance
metrics = IngestionMetrics()

# Decorator for automatic request metrics
def track_request_metrics(func):
    """Decorator to automatically track request metrics"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        method = "GET"  # Default, should be extracted from request
        endpoint = func.__name__
        status = 200
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = 500
            metrics.record_error("request_error", "ingestion_service")
            raise
        finally:
            duration = time.time() - start_time
            metrics.record_request(method, endpoint, status, duration)
    
    return wrapper

# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations"""
    
    def __init__(self, metric_func, *labels):
        self.metric_func = metric_func
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metric_func(*self.labels, duration)

# Example usage:
# with MetricsTimer(metrics.record_storage_operation, "upload", "success"):
#     # Storage operation code
#     pass
