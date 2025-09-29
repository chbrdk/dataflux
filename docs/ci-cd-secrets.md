# DataFlux CI/CD Secrets Management
# Documentation for required secrets and environment variables

## Required GitHub Secrets

### Container Registry
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- `DOCKER_USERNAME`: Username for container registry
- `DOCKER_PASSWORD`: Password/token for container registry

### Security Scanning
- `SNYK_TOKEN`: Snyk API token for security scanning
- `TRIVY_TOKEN`: Trivy API token (optional, for enhanced scanning)

### Deployment
- `KUBECONFIG`: Kubernetes configuration for deployment
- `HELM_REPO_URL`: Helm repository URL
- `HELM_REPO_USERNAME`: Helm repository username
- `HELM_REPO_PASSWORD`: Helm repository password

### Database
- `POSTGRES_PASSWORD`: PostgreSQL password for tests
- `REDIS_PASSWORD`: Redis password for tests
- `KAFKA_PASSWORD`: Kafka password for tests

### External Services
- `OPENAI_API_KEY`: OpenAI API key for MCP Server
- `ELEVENLABS_API_KEY`: ElevenLabs API key for voice features
- `WEAVIATE_API_KEY`: Weaviate API key
- `NEO4J_PASSWORD`: Neo4j password

### Monitoring
- `PROMETHEUS_URL`: Prometheus server URL
- `GRAFANA_URL`: Grafana server URL
- `GRAFANA_API_KEY`: Grafana API key

### Notifications
- `SLACK_WEBHOOK_URL`: Slack webhook for notifications
- `DISCORD_WEBHOOK_URL`: Discord webhook for notifications
- `EMAIL_SMTP_HOST`: SMTP host for email notifications
- `EMAIL_SMTP_USER`: SMTP username
- `EMAIL_SMTP_PASSWORD`: SMTP password

## Environment Variables

### Development
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=2001
POSTGRES_USER=dataflux_user
POSTGRES_PASSWORD=dataflux_pass
POSTGRES_DB=dataflux

# Redis
REDIS_HOST=localhost
REDIS_PORT=2002
REDIS_PASSWORD=dataflux_pass

# Kafka
KAFKA_HOST=localhost
KAFKA_PORT=2009
KAFKA_PASSWORD=dataflux_pass

# MinIO
MINIO_HOST=localhost
MINIO_PORT=2003
MINIO_ACCESS_KEY=dataflux_user
MINIO_SECRET_KEY=dataflux_pass

# Weaviate
WEAVIATE_HOST=localhost
WEAVIATE_PORT=2005
WEAVIATE_API_KEY=your_api_key

# Neo4j
NEO4J_HOST=localhost
NEO4J_PORT=2007
NEO4J_USER=neo4j
NEO4J_PASSWORD=dataflux_pass

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=2011
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# Services
INGESTION_SERVICE_URL=http://localhost:8002
QUERY_SERVICE_URL=http://localhost:8003
ANALYSIS_SERVICE_URL=http://localhost:8004
MCP_SERVER_URL=http://localhost:2015
WEB_UI_URL=http://localhost:3000
API_GATEWAY_URL=http://localhost:2013

# Monitoring
PROMETHEUS_URL=http://localhost:2020
GRAFANA_URL=http://localhost:2021
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

### Staging
```bash
# Database
POSTGRES_HOST=staging-postgres.dataflux.local
POSTGRES_PORT=5432
POSTGRES_USER=dataflux_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=dataflux_staging

# Redis
REDIS_HOST=staging-redis.dataflux.local
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}

# Kafka
KAFKA_HOST=staging-kafka.dataflux.local
KAFKA_PORT=9092
KAFKA_PASSWORD=${KAFKA_PASSWORD}

# Services
INGESTION_SERVICE_URL=https://staging-ingestion.dataflux.local
QUERY_SERVICE_URL=https://staging-query.dataflux.local
ANALYSIS_SERVICE_URL=https://staging-analysis.dataflux.local
MCP_SERVER_URL=https://staging-mcp.dataflux.local
WEB_UI_URL=https://staging.dataflux.local
API_GATEWAY_URL=https://staging-api.dataflux.local

# Monitoring
PROMETHEUS_URL=https://staging-prometheus.dataflux.local
GRAFANA_URL=https://staging-grafana.dataflux.local
GRAFANA_USER=admin
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
```

### Production
```bash
# Database
POSTGRES_HOST=prod-postgres.dataflux.local
POSTGRES_PORT=5432
POSTGRES_USER=dataflux_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=dataflux_prod

# Redis
REDIS_HOST=prod-redis.dataflux.local
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}

# Kafka
KAFKA_HOST=prod-kafka.dataflux.local
KAFKA_PORT=9092
KAFKA_PASSWORD=${KAFKA_PASSWORD}

# Services
INGESTION_SERVICE_URL=https://ingestion.dataflux.local
QUERY_SERVICE_URL=https://query.dataflux.local
ANALYSIS_SERVICE_URL=https://analysis.dataflux.local
MCP_SERVER_URL=https://mcp.dataflux.local
WEB_UI_URL=https://dataflux.local
API_GATEWAY_URL=https://api.dataflux.local

# Monitoring
PROMETHEUS_URL=https://prometheus.dataflux.local
GRAFANA_URL=https://grafana.dataflux.local
GRAFANA_USER=admin
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
```

## Security Best Practices

### Secret Management
1. **Never commit secrets to code**
2. **Use GitHub Secrets for sensitive data**
3. **Rotate secrets regularly**
4. **Use least privilege principle**
5. **Encrypt secrets at rest**

### Environment Separation
1. **Separate environments completely**
2. **Use different credentials per environment**
3. **Isolate network access**
4. **Monitor access patterns**

### Access Control
1. **Use service accounts for CI/CD**
2. **Limit permissions to minimum required**
3. **Audit access regularly**
4. **Use multi-factor authentication**

## Setup Instructions

### 1. GitHub Secrets Setup
```bash
# Navigate to repository settings
# Go to Secrets and variables > Actions
# Add each required secret

# Example for container registry
DOCKER_USERNAME: your-registry-username
DOCKER_PASSWORD: your-registry-token
```

### 2. Environment Setup
```bash
# Create environment-specific files
cp .env.example .env.development
cp .env.example .env.staging
cp .env.example .env.production

# Update with appropriate values
# Never commit .env files to version control
```

### 3. Security Scanning Setup
```bash
# Get Snyk token
# Visit https://snyk.io/
# Create account and get API token
# Add to GitHub Secrets as SNYK_TOKEN

# Get Trivy token (optional)
# Visit https://trivy.dev/
# Create account and get API token
# Add to GitHub Secrets as TRIVY_TOKEN
```

### 4. Deployment Setup
```bash
# Setup Kubernetes access
# Generate kubeconfig for CI/CD
# Add to GitHub Secrets as KUBECONFIG

# Setup Helm repository
# Add repository credentials to GitHub Secrets
HELM_REPO_URL: https://your-helm-repo.com
HELM_REPO_USERNAME: your-username
HELM_REPO_PASSWORD: your-password
```

## Monitoring and Alerting

### Health Checks
- All services must respond to `/health` endpoint
- Database connections must be verified
- External service dependencies must be checked

### Alerts
- Failed deployments
- Security vulnerabilities
- Performance degradation
- Service outages

### Notifications
- Slack channel for team notifications
- Discord webhook for development updates
- Email alerts for critical issues
- SMS alerts for production outages
