"""
DataFlux Analysis Service - Document Processing Monitoring
Provides comprehensive monitoring and metrics for document analysis performance
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class ProcessingMetrics:
    """Metrics for document processing performance"""
    document_id: str
    document_type: str
    file_size: int
    processing_time: float
    segments_extracted: int
    features_extracted: int
    embeddings_generated: int
    cache_hit: bool
    error_occurred: bool
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class SystemMetrics:
    """System-wide performance metrics"""
    total_documents_processed: int
    average_processing_time: float
    cache_hit_rate: float
    error_rate: float
    documents_per_minute: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class DocumentMonitoring:
    """Comprehensive monitoring system for document processing"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.processing_history = deque(maxlen=max_history)
        self.error_history = deque(maxlen=100)
        self.performance_windows = {
            '1min': deque(maxlen=60),
            '5min': deque(maxlen=300),
            '15min': deque(maxlen=900),
            '1hour': deque(maxlen=3600)
        }
        
        # Performance counters
        self.counters = {
            'total_documents': 0,
            'total_processing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'segments_total': 0,
            'features_total': 0,
            'embeddings_total': 0
        }
        
        # Document type statistics
        self.document_type_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'errors': 0
        })
        
        # Performance alerts
        self.alert_thresholds = {
            'max_processing_time': 30.0,  # seconds
            'min_cache_hit_rate': 0.7,    # 70%
            'max_error_rate': 0.05,      # 5%
            'max_memory_usage': 2048,    # MB
            'max_cpu_usage': 80.0        # percent
        }
        
        self.alerts = deque(maxlen=50)
        
    async def record_processing(self, metrics: ProcessingMetrics):
        """Record document processing metrics"""
        try:
            # Add to history
            self.processing_history.append(metrics)
            
            # Update counters
            self.counters['total_documents'] += 1
            self.counters['total_processing_time'] += metrics.processing_time
            self.counters['segments_total'] += metrics.segments_extracted
            self.counters['features_total'] += metrics.features_extracted
            self.counters['embeddings_generated'] += metrics.embeddings_generated
            
            if metrics.cache_hit:
                self.counters['cache_hits'] += 1
            else:
                self.counters['cache_misses'] += 1
                
            if metrics.error_occurred:
                self.counters['errors'] += 1
                self.error_history.append(metrics)
            
            # Update document type statistics
            doc_type = metrics.document_type
            self.document_type_stats[doc_type]['count'] += 1
            self.document_type_stats[doc_type]['total_time'] += metrics.processing_time
            self.document_type_stats[doc_type]['avg_time'] = (
                self.document_type_stats[doc_type]['total_time'] / 
                self.document_type_stats[doc_type]['count']
            )
            
            if metrics.error_occurred:
                self.document_type_stats[doc_type]['errors'] += 1
            
            # Update performance windows
            for window_name, window_data in self.performance_windows.items():
                window_data.append(metrics)
            
            # Check for performance alerts
            await self._check_performance_alerts(metrics)
            
            logger.info(f"📊 Processing metrics recorded: {metrics.document_id} - {metrics.processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to record processing metrics: {str(e)}")
    
    async def _check_performance_alerts(self, metrics: ProcessingMetrics):
        """Check for performance alerts and generate warnings"""
        try:
            current_time = datetime.now()
            
            # Check processing time alert
            if metrics.processing_time > self.alert_thresholds['max_processing_time']:
                alert = {
                    'type': 'slow_processing',
                    'severity': 'warning',
                    'message': f"Slow processing detected: {metrics.document_id} took {metrics.processing_time:.2f}s",
                    'timestamp': current_time,
                    'document_id': metrics.document_id,
                    'processing_time': metrics.processing_time
                }
                self.alerts.append(alert)
                logger.warning(f"⚠️ Slow processing alert: {metrics.document_id}")
            
            # Check error rate
            recent_errors = sum(1 for m in list(self.processing_history)[-100:] if m.error_occurred)
            recent_total = min(100, len(self.processing_history))
            if recent_total > 0:
                error_rate = recent_errors / recent_total
                if error_rate > self.alert_thresholds['max_error_rate']:
                    alert = {
                        'type': 'high_error_rate',
                        'severity': 'critical',
                        'message': f"High error rate detected: {error_rate:.2%}",
                        'timestamp': current_time,
                        'error_rate': error_rate
                    }
                    self.alerts.append(alert)
                    logger.error(f"🚨 High error rate alert: {error_rate:.2%}")
            
        except Exception as e:
            logger.error(f"Failed to check performance alerts: {str(e)}")
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system-wide metrics"""
        try:
            total_docs = self.counters['total_documents']
            total_time = self.counters['total_processing_time']
            
            avg_processing_time = total_time / total_docs if total_docs > 0 else 0.0
            
            cache_total = self.counters['cache_hits'] + self.counters['cache_misses']
            cache_hit_rate = self.counters['cache_hits'] / cache_total if cache_total > 0 else 0.0
            
            error_rate = self.counters['errors'] / total_docs if total_docs > 0 else 0.0
            
            # Calculate documents per minute (last 5 minutes)
            recent_metrics = list(self.performance_windows['5min'])
            if len(recent_metrics) > 1:
                time_span = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds() / 60
                docs_per_minute = len(recent_metrics) / max(time_span, 1) if time_span > 0 else 0
            else:
                docs_per_minute = 0.0
            
            return SystemMetrics(
                total_documents_processed=total_docs,
                average_processing_time=avg_processing_time,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                documents_per_minute=docs_per_minute,
                memory_usage_mb=0.0,  # Would need system monitoring
                cpu_usage_percent=0.0  # Would need system monitoring
            )
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {str(e)}")
            return SystemMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def get_document_type_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics by document type"""
        return dict(self.document_type_stats)
    
    def get_performance_trends(self, window: str = '5min') -> Dict[str, Any]:
        """Get performance trends for specified time window"""
        try:
            if window not in self.performance_windows:
                window = '5min'
            
            metrics_list = list(self.performance_windows[window])
            if not metrics_list:
                return {'trend': 'no_data', 'processing_times': [], 'throughput': 0}
            
            processing_times = [m.processing_time for m in metrics_list]
            throughput = len(metrics_list)
            
            # Calculate trend
            if len(processing_times) >= 2:
                recent_avg = statistics.mean(processing_times[-10:]) if len(processing_times) >= 10 else statistics.mean(processing_times)
                older_avg = statistics.mean(processing_times[:-10]) if len(processing_times) >= 20 else statistics.mean(processing_times)
                
                if recent_avg > older_avg * 1.1:
                    trend = 'degrading'
                elif recent_avg < older_avg * 0.9:
                    trend = 'improving'
                else:
                    trend = 'stable'
            else:
                trend = 'insufficient_data'
            
            return {
                'trend': trend,
                'processing_times': processing_times,
                'throughput': throughput,
                'avg_processing_time': statistics.mean(processing_times) if processing_times else 0.0,
                'median_processing_time': statistics.median(processing_times) if processing_times else 0.0,
                'p95_processing_time': statistics.quantiles(processing_times, n=20)[18] if len(processing_times) >= 20 else (max(processing_times) if processing_times else 0.0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {str(e)}")
            return {'trend': 'error', 'processing_times': [], 'throughput': 0}
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent performance alerts"""
        return list(self.alerts)[-limit:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary and patterns"""
        try:
            if not self.error_history:
                return {'total_errors': 0, 'error_patterns': {}, 'recent_errors': []}
            
            error_patterns = defaultdict(int)
            recent_errors = []
            
            for error_metric in self.error_history:
                if error_metric.error_message:
                    error_patterns[error_metric.error_message] += 1
                
                recent_errors.append({
                    'document_id': error_metric.document_id,
                    'document_type': error_metric.document_type,
                    'error_message': error_metric.error_message,
                    'timestamp': error_metric.timestamp.isoformat()
                })
            
            return {
                'total_errors': len(self.error_history),
                'error_patterns': dict(error_patterns),
                'recent_errors': recent_errors[-10:]  # Last 10 errors
            }
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {str(e)}")
            return {'total_errors': 0, 'error_patterns': {}, 'recent_errors': []}
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external monitoring systems"""
        try:
            return {
                'system_metrics': asdict(self.get_system_metrics()),
                'document_type_stats': self.get_document_type_stats(),
                'performance_trends': {
                    '1min': self.get_performance_trends('1min'),
                    '5min': self.get_performance_trends('5min'),
                    '15min': self.get_performance_trends('15min'),
                    '1hour': self.get_performance_trends('1hour')
                },
                'recent_alerts': self.get_recent_alerts(),
                'error_summary': self.get_error_summary(),
                'counters': self.counters.copy(),
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {str(e)}")
            return {'error': str(e)}
    
    def reset_metrics(self):
        """Reset all metrics (for testing or maintenance)"""
        self.processing_history.clear()
        self.error_history.clear()
        for window in self.performance_windows.values():
            window.clear()
        self.alerts.clear()
        self.counters.clear()
        self.document_type_stats.clear()
        logger.info("📊 All monitoring metrics reset")

# Global monitoring instance
document_monitor = DocumentMonitoring()

# Convenience functions for easy integration
async def record_document_processing(
    document_id: str,
    document_type: str,
    file_size: int,
    processing_time: float,
    segments_extracted: int,
    features_extracted: int,
    embeddings_generated: int,
    cache_hit: bool = False,
    error_occurred: bool = False,
    error_message: Optional[str] = None
):
    """Record document processing metrics"""
    metrics = ProcessingMetrics(
        document_id=document_id,
        document_type=document_type,
        file_size=file_size,
        processing_time=processing_time,
        segments_extracted=segments_extracted,
        features_extracted=features_extracted,
        embeddings_generated=embeddings_generated,
        cache_hit=cache_hit,
        error_occurred=error_occurred,
        error_message=error_message
    )
    
    await document_monitor.record_processing(metrics)

def get_monitoring_dashboard_data() -> Dict[str, Any]:
    """Get data for monitoring dashboard"""
    return document_monitor.export_metrics()

# Test function
async def test_monitoring():
    """Test the monitoring system"""
    print("🧪 Testing Document Monitoring System")
    print("=" * 50)
    
    # Simulate some processing metrics
    test_metrics = [
        ProcessingMetrics("doc1", "pdf", 1024000, 2.5, 15, 8, 3, False, False),
        ProcessingMetrics("doc2", "html", 512000, 1.2, 8, 5, 2, True, False),
        ProcessingMetrics("doc3", "docx", 2048000, 4.1, 25, 12, 5, False, False),
        ProcessingMetrics("doc4", "pdf", 1536000, 3.8, 20, 10, 4, True, False),
        ProcessingMetrics("doc5", "html", 256000, 0.8, 5, 3, 1, False, True, "Parsing error"),
    ]
    
    # Record metrics
    for metrics in test_metrics:
        await document_monitor.record_processing(metrics)
    
    # Get system metrics
    system_metrics = document_monitor.get_system_metrics()
    print(f"📊 System Metrics:")
    print(f"   Total Documents: {system_metrics.total_documents_processed}")
    print(f"   Avg Processing Time: {system_metrics.average_processing_time:.2f}s")
    print(f"   Cache Hit Rate: {system_metrics.cache_hit_rate:.2%}")
    print(f"   Error Rate: {system_metrics.error_rate:.2%}")
    print(f"   Documents/Min: {system_metrics.documents_per_minute:.1f}")
    
    # Get document type stats
    doc_type_stats = document_monitor.get_document_type_stats()
    print(f"\n📄 Document Type Statistics:")
    for doc_type, stats in doc_type_stats.items():
        print(f"   {doc_type}: {stats['count']} docs, avg {stats['avg_time']:.2f}s")
    
    # Get performance trends
    trends = document_monitor.get_performance_trends('5min')
    print(f"\n📈 Performance Trends:")
    print(f"   Trend: {trends['trend']}")
    print(f"   Throughput: {trends['throughput']} docs")
    if 'avg_processing_time' in trends:
        print(f"   Avg Time: {trends['avg_processing_time']:.2f}s")
    
    # Get alerts
    alerts = document_monitor.get_recent_alerts()
    print(f"\n🚨 Recent Alerts: {len(alerts)}")
    for alert in alerts:
        print(f"   {alert['severity'].upper()}: {alert['message']}")
    
    # Get error summary
    error_summary = document_monitor.get_error_summary()
    print(f"\n❌ Error Summary:")
    print(f"   Total Errors: {error_summary['total_errors']}")
    print(f"   Error Patterns: {error_summary['error_patterns']}")
    
    print("\n✅ Monitoring system test completed!")

if __name__ == "__main__":
    asyncio.run(test_monitoring())
