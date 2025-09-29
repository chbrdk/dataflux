# DataFlux Scripts & Utilities

## 🛠️ Overview

This directory contains utility scripts for setup, deployment, monitoring, and maintenance of DataFlux.

## 📁 Structure

```
scripts/
├── backup/                # Backup and recovery scripts
│   ├── backup.sh         # Full system backup
│   ├── restore.sh        # System restoration
│   └── verify.sh         # Backup verification
├── monitoring/            # Monitoring and health checks
│   ├── health-check.sh   # System health check
│   ├── metrics.sh        # Metrics collection
│   └── alerts.sh         # Alert management
├── deployment/            # Deployment scripts
│   ├── deploy.sh         # Production deployment
│   ├── rollback.sh       # Rollback deployment
│   └── update.sh         # Update services
├── maintenance/           # Maintenance scripts
│   ├── cleanup.sh        # System cleanup
│   ├── optimize.sh       # Performance optimization
│   └── migrate.sh        # Database migration
└── development/           # Development utilities
    ├── setup-dev.sh      # Development setup
    ├── test-env.sh       # Test environment
    └── debug.sh          # Debugging utilities
```

## 🚀 Quick Start

### Development Setup
```bash
# Run development setup
./scripts/development/setup-dev.sh

# Start development environment
make dev

# Run health check
./scripts/monitoring/health-check.sh
```

### Production Deployment
```bash
# Deploy to production
./scripts/deployment/deploy.sh production

# Check deployment status
./scripts/monitoring/health-check.sh

# Run backup
./scripts/backup/backup.sh
```

## 🔧 Script Categories

### Backup & Recovery
- **Full Backup**: Complete system backup
- **Incremental Backup**: Delta backups
- **Restore**: System restoration
- **Verification**: Backup integrity checks

### Monitoring & Health
- **Health Checks**: Service health monitoring
- **Metrics Collection**: Performance metrics
- **Alert Management**: Alert configuration
- **Log Analysis**: Log processing

### Deployment
- **Production Deploy**: Production deployment
- **Staging Deploy**: Staging deployment
- **Rollback**: Deployment rollback
- **Update**: Service updates

### Maintenance
- **Cleanup**: System cleanup
- **Optimization**: Performance tuning
- **Migration**: Database migrations
- **Security**: Security updates

## 📋 Script Examples

### Health Check Script
```bash
#!/bin/bash
# scripts/monitoring/health-check.sh

set -e

echo "DataFlux Health Check"
echo "==================="

# Check services
services=("postgres" "redis" "kafka" "minio" "weaviate" "neo4j")

for service in "${services[@]}"; do
    echo "Checking $service..."
    if docker-compose ps $service | grep -q "Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
        exit 1
    fi
done

# Check API endpoints
echo "Checking API endpoints..."
curl -f http://localhost/health || exit 1
curl -f http://localhost/api/v1/assets || exit 1

echo "✅ All health checks passed"
```

### Backup Script
```bash
#!/bin/bash
# scripts/backup/backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting DataFlux backup..."

# PostgreSQL backup
echo "Backing up PostgreSQL..."
docker-compose exec -T postgres pg_dump -U dataflux_user dataflux | gzip > "$BACKUP_DIR/postgres.sql.gz"

# Redis backup
echo "Backing up Redis..."
docker-compose exec -T redis redis-cli --rdb /data/dump.rdb BGSAVE
sleep 5
docker cp dataflux-redis:/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# MinIO backup
echo "Backing up MinIO..."
docker-compose exec -T minio mc mirror --overwrite minio/dataflux-assets "$BACKUP_DIR/minio/"

echo "Backup completed: $BACKUP_DIR"
```

### Deployment Script
```bash
#!/bin/bash
# scripts/deployment/deploy.sh

set -e

ENVIRONMENT=${1:-development}

echo "Deploying DataFlux to $ENVIRONMENT..."

# Build images
echo "Building Docker images..."
docker-compose build

# Deploy services
echo "Deploying services..."
docker-compose -f docker-compose.yml -f "docker-compose.$ENVIRONMENT.yml" up -d

# Wait for services
echo "Waiting for services to be ready..."
sleep 30

# Run health check
echo "Running health check..."
./scripts/monitoring/health-check.sh

echo "✅ Deployment completed successfully"
```

## 🔄 Automation

### Cron Jobs
```bash
# Add to crontab for automated tasks
# Daily backup at 2 AM
0 2 * * * /path/to/dataflux/scripts/backup/backup.sh

# Health check every 5 minutes
*/5 * * * * /path/to/dataflux/scripts/monitoring/health-check.sh

# Cleanup every Sunday at 3 AM
0 3 * * 0 /path/to/dataflux/scripts/maintenance/cleanup.sh
```

### CI/CD Integration
```yaml
# .github/workflows/deploy.yml
name: Deploy DataFlux

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: ./scripts/deployment/deploy.sh production
      - name: Health check
        run: ./scripts/monitoring/health-check.sh
```

## 📊 Monitoring Scripts

### Metrics Collection
```bash
#!/bin/bash
# scripts/monitoring/metrics.sh

# Collect system metrics
echo "Collecting system metrics..."

# CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
echo "CPU Usage: $CPU_USAGE%"

# Memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')
echo "Memory Usage: $MEMORY_USAGE%"

# Disk usage
DISK_USAGE=$(df -h / | awk 'NR==2{printf "%s", $5}')
echo "Disk Usage: $DISK_USAGE"

# Send to monitoring system
curl -X POST http://localhost:9090/api/v1/write \
  -H "Content-Type: application/json" \
  -d "{\"cpu_usage\": $CPU_USAGE, \"memory_usage\": $MEMORY_USAGE, \"disk_usage\": \"$DISK_USAGE\"}"
```

### Alert Management
```bash
#!/bin/bash
# scripts/monitoring/alerts.sh

# Check for critical alerts
echo "Checking for critical alerts..."

# Check service status
if ! docker-compose ps | grep -q "Up"; then
    echo "ALERT: Some services are down"
    # Send alert to Slack/Email
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"DataFlux Alert: Services down"}' \
      $SLACK_WEBHOOK_URL
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "ALERT: Disk usage is high ($DISK_USAGE%)"
    # Send alert
fi
```

## 🧹 Maintenance Scripts

### System Cleanup
```bash
#!/bin/bash
# scripts/maintenance/cleanup.sh

echo "Starting system cleanup..."

# Clean Docker
echo "Cleaning Docker..."
docker system prune -f
docker volume prune -f

# Clean logs
echo "Cleaning logs..."
find /var/log -name "*.log" -mtime +7 -delete

# Clean temporary files
echo "Cleaning temporary files..."
find /tmp -type f -mtime +1 -delete

# Clean old backups
echo "Cleaning old backups..."
find /backups -type d -mtime +30 -exec rm -rf {} \;

echo "✅ Cleanup completed"
```

### Performance Optimization
```bash
#!/bin/bash
# scripts/maintenance/optimize.sh

echo "Optimizing DataFlux performance..."

# Optimize PostgreSQL
echo "Optimizing PostgreSQL..."
docker-compose exec postgres psql -U dataflux_user -d dataflux -c "VACUUM ANALYZE;"

# Optimize Redis
echo "Optimizing Redis..."
docker-compose exec redis redis-cli --eval "return redis.call('MEMORY', 'PURGE')"

# Optimize MinIO
echo "Optimizing MinIO..."
docker-compose exec minio mc admin heal minio/dataflux-assets

echo "✅ Optimization completed"
```

## 🔒 Security Scripts

### Security Audit
```bash
#!/bin/bash
# scripts/security/audit.sh

echo "Running security audit..."

# Check for security updates
echo "Checking for security updates..."
apt list --upgradable | grep -i security

# Check Docker images
echo "Scanning Docker images..."
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image dataflux/ingestion-service:latest

# Check file permissions
echo "Checking file permissions..."
find /app -type f -perm /o+w -ls

echo "✅ Security audit completed"
```

## 📋 Script Checklist

- [ ] All scripts have proper error handling
- [ ] Scripts are executable and have shebang
- [ ] Documentation updated for each script
- [ ] Scripts tested in different environments
- [ ] Logging implemented for all scripts
- [ ] Backup scripts verified
- [ ] Health check scripts working
- [ ] Deployment scripts tested
- [ ] Maintenance scripts scheduled
- [ ] Security scripts implemented
- [ ] CI/CD integration working
- [ ] Monitoring scripts configured
- [ ] Alert scripts tested
- [ ] Performance scripts optimized
- [ ] Documentation complete
