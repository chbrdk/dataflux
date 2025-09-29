# DataFlux Environment Configuration
# Production environment settings for Kubernetes deployment

# Environment Variables
export NAMESPACE="dataflux"
export ENVIRONMENT="production"
export LOG_LEVEL="info"

# Database Configuration
export POSTGRES_HOST="postgres-service"
export POSTGRES_PORT="5432"
export POSTGRES_USER="dataflux_user"
export POSTGRES_DB="dataflux"
export POSTGRES_PASSWORD="dataflux_pass"

# Redis Configuration
export REDIS_HOST="redis-service"
export REDIS_PORT="6379"
export REDIS_PASSWORD="dataflux_pass"

# Kafka Configuration
export KAFKA_BOOTSTRAP_SERVERS="kafka-service:9092"

# MinIO Configuration
export MINIO_ENDPOINT="minio-service:9000"
export MINIO_BUCKET="dataflux-assets"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"

# Weaviate Configuration
export WEAVIATE_HOST="weaviate-service"
export WEAVIATE_PORT="8080"

# Neo4j Configuration
export NEO4J_HOST="neo4j-service"
export NEO4J_PORT="7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="dataflux_pass"

# ClickHouse Configuration
export CLICKHOUSE_HOST="clickhouse-service"
export CLICKHOUSE_PORT="9000"
export CLICKHOUSE_USER="default"
export CLICKHOUSE_PASSWORD=""

# Service URLs
export INGESTION_SERVICE_URL="http://ingestion-service:8002"
export QUERY_SERVICE_URL="http://query-service:8003"
export ANALYSIS_SERVICE_URL="http://analysis-service:8004"
export AUTH_SERVICE_URL="http://auth-service:8006"
export MCP_SERVER_URL="http://mcp-server:2015"

# Security Configuration
export JWT_SECRET_KEY="super-secret-key-change-in-production"
export CORS_ORIGINS="https://dataflux.com,https://app.dataflux.com"

# Performance Configuration
export MAX_WORKERS="4"
export WORKER_TIMEOUT="300"
export REQUEST_TIMEOUT="30"

# Rate Limiting
export RATE_LIMIT_REQUESTS="1000"
export RATE_LIMIT_WINDOW="3600"

# Monitoring Configuration
export PROMETHEUS_ENDPOINT="http://prometheus:9090"
export GRAFANA_ENDPOINT="http://grafana:3000"

# Storage Configuration
export STORAGE_CLASS="fast-ssd"
export POSTGRES_STORAGE_SIZE="50Gi"
export MINIO_STORAGE_SIZE="100Gi"
export WEAVIATE_STORAGE_SIZE="50Gi"
export NEO4J_STORAGE_SIZE="50Gi"
export CLICKHOUSE_STORAGE_SIZE="50Gi"

# Scaling Configuration
export INGESTION_MIN_REPLICAS="2"
export INGESTION_MAX_REPLICAS="10"
export QUERY_MIN_REPLICAS="2"
export QUERY_MAX_REPLICAS="15"
export ANALYSIS_MIN_REPLICAS="1"
export ANALYSIS_MAX_REPLICAS="8"
export AUTH_MIN_REPLICAS="2"
export AUTH_MAX_REPLICAS="6"
export MCP_MIN_REPLICAS="1"
export MCP_MAX_REPLICAS="5"
export WEB_UI_MIN_REPLICAS="2"
export WEB_UI_MAX_REPLICAS="8"
export API_GATEWAY_MIN_REPLICAS="2"
export API_GATEWAY_MAX_REPLICAS="10"

# Resource Limits
export INGESTION_CPU_REQUEST="250m"
export INGESTION_CPU_LIMIT="1000m"
export INGESTION_MEMORY_REQUEST="512Mi"
export INGESTION_MEMORY_LIMIT="2Gi"

export QUERY_CPU_REQUEST="250m"
export QUERY_CPU_LIMIT="1000m"
export QUERY_MEMORY_REQUEST="512Mi"
export QUERY_MEMORY_LIMIT="2Gi"

export ANALYSIS_CPU_REQUEST="500m"
export ANALYSIS_CPU_LIMIT="2000m"
export ANALYSIS_MEMORY_REQUEST="1Gi"
export ANALYSIS_MEMORY_LIMIT="4Gi"

export AUTH_CPU_REQUEST="100m"
export AUTH_CPU_LIMIT="500m"
export AUTH_MEMORY_REQUEST="256Mi"
export AUTH_MEMORY_LIMIT="1Gi"

export MCP_CPU_REQUEST="100m"
export MCP_CPU_LIMIT="500m"
export MCP_MEMORY_REQUEST="256Mi"
export MCP_MEMORY_LIMIT="1Gi"

export WEB_UI_CPU_REQUEST="100m"
export WEB_UI_CPU_LIMIT="250m"
export WEB_UI_MEMORY_REQUEST="256Mi"
export WEB_UI_MEMORY_LIMIT="512Mi"

export API_GATEWAY_CPU_REQUEST="100m"
export API_GATEWAY_CPU_LIMIT="250m"
export API_GATEWAY_MEMORY_REQUEST="128Mi"
export API_GATEWAY_MEMORY_LIMIT="256Mi"

# Database Resource Limits
export POSTGRES_CPU_REQUEST="250m"
export POSTGRES_CPU_LIMIT="1000m"
export POSTGRES_MEMORY_REQUEST="512Mi"
export POSTGRES_MEMORY_LIMIT="2Gi"

export REDIS_CPU_REQUEST="100m"
export REDIS_CPU_LIMIT="500m"
export REDIS_MEMORY_REQUEST="256Mi"
export REDIS_MEMORY_LIMIT="1Gi"

export KAFKA_CPU_REQUEST="250m"
export KAFKA_CPU_LIMIT="1000m"
export KAFKA_MEMORY_REQUEST="512Mi"
export KAFKA_MEMORY_LIMIT="2Gi"

export MINIO_CPU_REQUEST="100m"
export MINIO_CPU_LIMIT="500m"
export MINIO_MEMORY_REQUEST="256Mi"
export MINIO_MEMORY_LIMIT="1Gi"

export WEAVIATE_CPU_REQUEST="500m"
export WEAVIATE_CPU_LIMIT="2000m"
export WEAVIATE_MEMORY_REQUEST="1Gi"
export WEAVIATE_MEMORY_LIMIT="4Gi"

export NEO4J_CPU_REQUEST="500m"
export NEO4J_CPU_LIMIT="2000m"
export NEO4J_MEMORY_REQUEST="1Gi"
export NEO4J_MEMORY_LIMIT="4Gi"

export CLICKHOUSE_CPU_REQUEST="500m"
export CLICKHOUSE_CPU_LIMIT="2000m"
export CLICKHOUSE_MEMORY_REQUEST="1Gi"
export CLICKHOUSE_MEMORY_LIMIT="4Gi"

# Monitoring Resource Limits
export PROMETHEUS_CPU_REQUEST="250m"
export PROMETHEUS_CPU_LIMIT="1000m"
export PROMETHEUS_MEMORY_REQUEST="512Mi"
export PROMETHEUS_MEMORY_LIMIT="2Gi"

export GRAFANA_CPU_REQUEST="100m"
export GRAFANA_CPU_LIMIT="500m"
export GRAFANA_MEMORY_REQUEST="256Mi"
export GRAFANA_MEMORY_LIMIT="1Gi"

# Health Check Configuration
export HEALTH_CHECK_INITIAL_DELAY="30"
export HEALTH_CHECK_PERIOD="10"
export READINESS_CHECK_INITIAL_DELAY="5"
export READINESS_CHECK_PERIOD="5"

# SSL/TLS Configuration
export SSL_CERT_PATH="/etc/nginx/ssl/cert.pem"
export SSL_KEY_PATH="/etc/nginx/ssl/key.pem"
export SSL_PROTOCOLS="TLSv1.2 TLSv1.3"

# Backup Configuration
export BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
export BACKUP_RETENTION_DAYS="30"
export BACKUP_RETENTION_WEEKS="12"
export BACKUP_RETENTION_MONTHS="12"

# Logging Configuration
export LOG_FORMAT="json"
export LOG_OUTPUT="stdout"
export LOG_ROTATION_SIZE="100MB"
export LOG_ROTATION_COUNT="10"

# Feature Flags
export ENABLE_METRICS="true"
export ENABLE_TRACING="true"
export ENABLE_PROFILING="false"
export ENABLE_DEBUG="false"

# External Dependencies
export EXTERNAL_API_TIMEOUT="30s"
export EXTERNAL_API_RETRIES="3"
export EXTERNAL_API_RETRY_DELAY="1s"

# Cache Configuration
export CACHE_TTL="3600"  # 1 hour
export CACHE_MAX_SIZE="1000"
export CACHE_CLEANUP_INTERVAL="300"  # 5 minutes

# Queue Configuration
export QUEUE_BATCH_SIZE="100"
export QUEUE_PROCESSING_TIMEOUT="300"
export QUEUE_RETRY_ATTEMPTS="3"
export QUEUE_RETRY_DELAY="5"

# Search Configuration
export SEARCH_DEFAULT_LIMIT="20"
export SEARCH_MAX_LIMIT="100"
export SEARCH_TIMEOUT="30s"
export SEARCH_CACHE_TTL="1800"  # 30 minutes

# Upload Configuration
export UPLOAD_MAX_SIZE="100MB"
export UPLOAD_ALLOWED_TYPES="video/*,audio/*,image/*,application/pdf"
export UPLOAD_CHUNK_SIZE="8MB"
export UPLOAD_CONCURRENT_LIMIT="5"

# Analysis Configuration
export ANALYSIS_BATCH_SIZE="10"
export ANALYSIS_TIMEOUT="300"
export ANALYSIS_RETRY_ATTEMPTS="3"
export ANALYSIS_RETRY_DELAY="10"

# Security Configuration
export PASSWORD_MIN_LENGTH="8"
export PASSWORD_REQUIRE_UPPERCASE="true"
export PASSWORD_REQUIRE_LOWERCASE="true"
export PASSWORD_REQUIRE_NUMBERS="true"
export PASSWORD_REQUIRE_SYMBOLS="true"

export SESSION_TIMEOUT="3600"  # 1 hour
export SESSION_REFRESH_THRESHOLD="300"  # 5 minutes
export SESSION_MAX_CONCURRENT="5"

# API Configuration
export API_VERSION="v1"
export API_DOCS_ENABLED="true"
export API_RATE_LIMIT_ENABLED="true"
export API_CORS_ENABLED="true"

# WebSocket Configuration
export WS_HEARTBEAT_INTERVAL="30"
export WS_CONNECTION_TIMEOUT="300"
export WS_MAX_CONNECTIONS="1000"

# File Processing Configuration
export FILE_PROCESSING_TIMEOUT="600"  # 10 minutes
export FILE_PROCESSING_RETRY_ATTEMPTS="3"
export FILE_PROCESSING_RETRY_DELAY="30"

# Thumbnail Configuration
export THUMBNAIL_WIDTH="320"
export THUMBNAIL_HEIGHT="240"
export THUMBNAIL_QUALITY="80"
export THUMBNAIL_FORMAT="jpeg"

# Proxy Configuration
export PROXY_ENABLED="true"
export PROXY_CACHE_TTL="3600"
export PROXY_MAX_SIZE="100MB"
export PROXY_ALLOWED_TYPES="video/*,audio/*,image/*"

# Notification Configuration
export NOTIFICATION_ENABLED="true"
export NOTIFICATION_RETRY_ATTEMPTS="3"
export NOTIFICATION_RETRY_DELAY="5"
export NOTIFICATION_TIMEOUT="30"

# Metrics Configuration
export METRICS_ENABLED="true"
export METRICS_PORT="9090"
export METRICS_PATH="/metrics"
export METRICS_INTERVAL="15s"

# Tracing Configuration
export TRACING_ENABLED="true"
export TRACING_SAMPLE_RATE="0.1"
export TRACING_JAEGER_ENDPOINT="http://jaeger:14268/api/traces"

# Profiling Configuration
export PROFILING_ENABLED="false"
export PROFILING_PORT="6060"
export PROFILING_PATH="/debug/pprof"

# Debug Configuration
export DEBUG_ENABLED="false"
export DEBUG_PORT="8080"
export DEBUG_PATH="/debug"

# Development Configuration
export DEV_MODE="false"
export DEV_HOT_RELOAD="false"
export DEV_DEBUG_LOGS="false"

# Testing Configuration
export TEST_MODE="false"
export TEST_DATABASE="dataflux_test"
export TEST_CLEANUP="true"

# Production Configuration
export PROD_MODE="true"
export PROD_OPTIMIZE="true"
export PROD_COMPRESS="true"
export PROD_MINIFY="true"
