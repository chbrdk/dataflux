# DataFlux Troubleshooting Guide

## Quick Diagnostics

### System Health Check
```bash
# Check all services
./scripts/health-check.py

# Check specific service
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8006/health
```

### Service Status
```bash
# Docker services
docker-compose -f docker/docker-compose.yml ps

# System resources
htop
df -h
free -h
```

## Common Issues

### 1. Service Startup Problems

#### PostgreSQL Connection Failed
**Symptoms**: Services fail to start with database connection errors
**Solutions**:
```bash
# Check PostgreSQL status
docker logs dataflux-postgres-1

# Restart PostgreSQL
docker-compose -f docker/docker-compose.yml restart postgres

# Check connection
psql -h localhost -p 2001 -U dataflux_user -d dataflux -c "SELECT 1;"
```

#### Redis Connection Failed
**Symptoms**: Services fail to connect to Redis
**Solutions**:
```bash
# Check Redis status
docker logs dataflux-redis-1

# Test Redis connection
redis-cli -h localhost -p 2002 -a dataflux_pass ping

# Restart Redis
docker-compose -f docker/docker-compose.yml restart redis
```

#### Kafka Connection Failed
**Symptoms**: Message processing fails
**Solutions**:
```bash
# Check Kafka status
docker logs dataflux-kafka-1

# Check Kafka topics
docker exec dataflux-kafka-1 kafka-topics --bootstrap-server localhost:9092 --list

# Restart Kafka
docker-compose -f docker/docker-compose.yml restart kafka
```

### 2. Upload Issues

#### File Upload Fails
**Symptoms**: Files fail to upload with error messages
**Solutions**:
- Check file size limits (default: 100MB)
- Verify supported file formats
- Check MinIO service status
- Verify disk space availability

#### Processing Stuck
**Symptoms**: Assets remain in "processing" state
**Solutions**:
```bash
# Check processing queue
curl http://localhost:8004/api/v1/queue/status

# Restart analysis service
docker-compose -f docker/docker-compose.yml restart analysis-service

# Check system resources
htop
```

### 3. Search Problems

#### No Search Results
**Symptoms**: Search returns empty results
**Solutions**:
- Verify assets are processed
- Check Weaviate service status
- Verify search query syntax
- Check database indexes

#### Slow Search Performance
**Symptoms**: Search queries take too long
**Solutions**:
- Check system resource usage
- Verify database performance
- Check cache status
- Optimize search queries

### 4. Authentication Issues

#### Login Fails
**Symptoms**: Cannot login with correct credentials
**Solutions**:
```bash
# Check auth service
curl http://localhost:8006/health

# Verify user exists
psql -h localhost -p 2001 -U dataflux_user -d dataflux -c "SELECT username FROM users;"

# Reset password
psql -h localhost -p 2001 -U dataflux_user -d dataflux -c "UPDATE users SET hashed_password = '\$2b\$12\$...' WHERE username = 'admin';"
```

#### Token Expired
**Symptoms**: API requests fail with authentication errors
**Solutions**:
- Refresh authentication token
- Check token expiration time
- Verify token format
- Re-authenticate if needed

## Error Codes

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request - Invalid input
- **401**: Unauthorized - Authentication required
- **403**: Forbidden - Insufficient permissions
- **404**: Not Found - Resource not found
- **500**: Internal Server Error - System error
- **503**: Service Unavailable - Service down

### Application Error Codes
- **ASSET_NOT_FOUND**: Asset does not exist
- **INVALID_FILE_FORMAT**: Unsupported file type
- **PROCESSING_FAILED**: Analysis processing failed
- **SEARCH_TIMEOUT**: Search query timeout
- **STORAGE_FULL**: Insufficient storage space

## Log Analysis

### Log Locations
```bash
# Application logs
/var/log/dataflux/

# Docker logs
docker logs <container_name>

# System logs
journalctl -u <service_name>
```

### Common Log Patterns
```bash
# Search for errors
grep -i "error" /var/log/dataflux/*.log

# Search for specific service
grep "ingestion" /var/log/dataflux/*.log

# Monitor real-time logs
tail -f /var/log/dataflux/ingestion.log
```

## Performance Issues

### High CPU Usage
**Symptoms**: System becomes slow, high CPU usage
**Solutions**:
- Check running processes
- Monitor resource usage
- Restart heavy services
- Scale services horizontally

### High Memory Usage
**Symptoms**: System runs out of memory
**Solutions**:
- Check memory usage per service
- Increase system memory
- Optimize service configurations
- Restart services

### Slow Database Queries
**Symptoms**: Database operations are slow
**Solutions**:
```sql
-- Check slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM assets WHERE collection_id = '123';

-- Check indexes
SELECT indexname, tablename FROM pg_indexes WHERE tablename = 'assets';
```

## Network Issues

### Connection Timeouts
**Symptoms**: Services cannot connect to each other
**Solutions**:
- Check network connectivity
- Verify firewall settings
- Check service ports
- Test network latency

### DNS Resolution
**Symptoms**: Services cannot resolve hostnames
**Solutions**:
- Check DNS configuration
- Verify /etc/hosts entries
- Test DNS resolution
- Use IP addresses instead of hostnames

## Recovery Procedures

### Service Recovery
```bash
# Restart all services
docker-compose -f docker/docker-compose.yml restart

# Restart specific service
docker-compose -f docker/docker-compose.yml restart <service_name>

# Rebuild service
docker-compose -f docker/docker-compose.yml up -d --build <service_name>
```

### Data Recovery
```bash
# Restore from backup
./scripts/recovery.sh automatic

# Verify backup integrity
./scripts/verify-backup.sh automatic

# Clean up old data
./scripts/retention.sh cleanup
```

### Configuration Recovery
```bash
# Reset to default configuration
cp docker/docker-compose.yml.backup docker/docker-compose.yml

# Restart services
docker-compose -f docker/docker-compose.yml restart
```

## Monitoring and Alerting

### Health Monitoring
```bash
# Check system health
./scripts/health-check.py

# Monitor service status
watch -n 5 'docker-compose -f docker/docker-compose.yml ps'

# Check resource usage
watch -n 5 'htop'
```

### Log Monitoring
```bash
# Monitor error logs
tail -f /var/log/dataflux/*.log | grep -i error

# Monitor access logs
tail -f /var/log/nginx/access.log

# Monitor system logs
journalctl -f
```

## Getting Help

### Support Channels
- **Documentation**: Check user guide and API docs
- **Logs**: Review system and application logs
- **Community**: Post questions in community forum
- **Support**: Contact technical support

### Information to Provide
When reporting issues, include:
- Error messages and logs
- Steps to reproduce
- System configuration
- Service versions
- Resource usage

### Useful Commands
```bash
# System information
uname -a
docker version
docker-compose version

# Service versions
docker images | grep dataflux

# Resource usage
df -h
free -h
htop

# Network connectivity
ping localhost
telnet localhost 2001
telnet localhost 2002
```
