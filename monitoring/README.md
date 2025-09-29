# DataFlux Monitoring & Observability

## 📊 Overview

This directory contains monitoring configurations for Prometheus, Grafana, and other observability tools.

## 📁 Structure

```
monitoring/
├── prometheus/            # Prometheus configuration
│   ├── prometheus.yml     # Main Prometheus config
│   ├── rules/             # Alerting rules
│   └── targets/           # Service discovery
├── grafana/               # Grafana configuration
│   ├── dashboards/        # Dashboard definitions
│   ├── datasources/       # Data source configs
│   └── provisioning/      # Auto-provisioning
├── alerts/                # Alert configurations
│   ├── slack.yml          # Slack notifications
│   ├── email.yml          # Email notifications
│   └── webhook.yml        # Webhook notifications
└── exporters/             # Custom exporters
    ├── dataflux-exporter/  # Custom metrics exporter
    └── logs/              # Log aggregation
```

## 🚀 Quick Start

### Start Monitoring Stack
```bash
# Start Prometheus and Grafana
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000
# Default credentials: admin/admin
```

### Import Dashboards
1. Open Grafana (http://localhost:3000)
2. Go to "+" → "Import"
3. Upload dashboard JSON files from `grafana/dashboards/`

## 📈 Metrics

### Service Metrics
- **Request Rate**: Requests per second
- **Response Time**: P50, P95, P99 latencies
- **Error Rate**: 4xx and 5xx error rates
- **Active Connections**: Current connections

### Business Metrics
- **Assets Processed**: Files processed per minute
- **Search Queries**: Search requests per second
- **Analysis Queue**: Queue depth and processing time
- **Storage Usage**: Disk usage by service

### System Metrics
- **CPU Usage**: Per service and overall
- **Memory Usage**: RAM consumption
- **Disk I/O**: Read/write operations
- **Network I/O**: Bytes in/out

## 🚨 Alerting

### Critical Alerts
- Service down > 1 minute
- Error rate > 5%
- Queue depth > 1000
- Disk usage > 80%
- Memory usage > 90%

### Warning Alerts
- Response time > 1 second
- CPU usage > 70%
- Low disk space < 20%
- High queue depth > 500

### Alert Channels
- **Slack**: #dataflux-alerts
- **Email**: admin@dataflux.local
- **Webhook**: Custom integrations

## 📊 Dashboards

### System Overview
- Service health status
- Resource utilization
- Request rates and errors
- Queue depths

### Application Metrics
- API endpoint performance
- Database query performance
- Cache hit rates
- Processing pipeline status

### Business Metrics
- Asset processing rates
- Search performance
- User activity
- Storage utilization

### Infrastructure
- Container health
- Network performance
- Disk usage
- Log analysis

## 🔧 Configuration

### Prometheus Configuration
```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dataflux-services'
    static_configs:
      - targets: ['ingestion-service:8001', 'query-service:8002']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Grafana Data Sources
```yaml
# grafana/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    access: proxy
    isDefault: true
```

## 📝 Custom Metrics

### Adding Custom Metrics
```python
# Python service example
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('dataflux_requests_total', 'Total requests', ['service', 'endpoint'])
REQUEST_DURATION = Histogram('dataflux_request_duration_seconds', 'Request duration')
QUEUE_SIZE = Gauge('dataflux_queue_size', 'Current queue size')

# Use in code
REQUEST_COUNT.labels(service='ingestion', endpoint='/upload').inc()
REQUEST_DURATION.observe(0.5)
QUEUE_SIZE.set(42)
```

### Go Service Example
```go
// Go service example
import "github.com/prometheus/client_golang/prometheus"

var (
    requestCount = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "dataflux_requests_total",
            Help: "Total requests",
        },
        []string{"service", "endpoint"},
    )
)

func init() {
    prometheus.MustRegister(requestCount)
}
```

## 🔍 Logging

### Log Levels
- **ERROR**: System errors, failures
- **WARN**: Recoverable issues, degraded performance
- **INFO**: Normal operations, state changes
- **DEBUG**: Detailed debugging information

### Log Format
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "ingestion-service",
  "request_id": "req-123",
  "message": "Asset uploaded successfully",
  "asset_id": "asset-456",
  "duration_ms": 150
}
```

### Log Aggregation
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Fluentd**: Log forwarding
- **Loki**: Log aggregation (Grafana)

## 🚀 Deployment

### Docker Compose
```yaml
# monitoring/docker-compose.monitoring.yml
version: '3.9'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./grafana:/etc/grafana
      - grafana_data:/var/lib/grafana
```

### Kubernetes
```yaml
# monitoring/k8s/prometheus-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
```

## 📋 Monitoring Checklist

- [ ] Prometheus configured and running
- [ ] Grafana dashboards imported
- [ ] Alert rules configured
- [ ] Notification channels set up
- [ ] Custom metrics implemented
- [ ] Log aggregation working
- [ ] Health checks configured
- [ ] Performance baselines established
- [ ] Documentation updated
- [ ] Team trained on monitoring tools
