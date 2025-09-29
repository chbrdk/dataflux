# DataFlux - Detaillierte Implementierungs-Spezifikation & Docker Setup

## 1. Projekt-Struktur

```
dataflux/
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── .env.example
├── services/
│   ├── api-gateway/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   └── configs/
│   ├── ingestion-service/
│   │   ├── Dockerfile
│   │   ├── src/
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   ├── analysis-service/
│   │   ├── Dockerfile
│   │   ├── src/
│   │   └── requirements.txt
│   ├── query-service/
│   │   ├── Dockerfile
│   │   ├── go.mod
│   │   ├── go.sum
│   │   └── cmd/
│   ├── mcp-server/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   └── web-ui/
│       ├── Dockerfile
│       ├── package.json
│       └── src/
├── shared/
│   ├── proto/
│   ├── schemas/
│   └── types/
├── scripts/
│   ├── init-db.sql
│   ├── create-topics.sh
│   └── setup-dev.sh
├── docs/
│   ├── api/
│   └── architecture/
├── Makefile
└── README.md
```

## 2. Docker Compose Konfiguration

### 2.1 Haupt docker-compose.yml

```yaml
version: '3.9'

x-common-variables: &common-variables
  TZ: ${TZ:-Europe/Berlin}
  LOG_LEVEL: ${LOG_LEVEL:-info}
  ENVIRONMENT: ${ENVIRONMENT:-development}

x-healthcheck-defaults: &healthcheck-defaults
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

services:
  # =================================
  # Core Databases
  # =================================
  
  postgres:
    image: postgres:16-alpine
    container_name: dataflux-postgres
    hostname: postgres
    restart: unless-stopped
    environment:
      <<: *common-variables
      POSTGRES_DB: ${POSTGRES_DB:-dataflux}
      POSTGRES_USER: ${POSTGRES_USER:-dataflux_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dataflux_pass}
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=en_US.UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-dataflux_user} -d ${POSTGRES_DB:-dataflux}"]
    networks:
      - dataflux-network

  weaviate:
    image: semitechnologies/weaviate:1.24.0
    container_name: dataflux-weaviate
    hostname: weaviate
    restart: unless-stopped
    environment:
      <<: *common-variables
      QUERY_DEFAULTS_LIMIT: 20
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'text2vec-transformers'
      ENABLE_MODULES: 'text2vec-transformers,text2vec-openai'
      CLUSTER_HOSTNAME: 'weaviate'
      AUTHENTICATION_APIKEY_ENABLED: 'true'
      AUTHENTICATION_APIKEY_ALLOWED_KEYS: ${WEAVIATE_API_KEY:-dataflux-key}
      AUTHENTICATION_APIKEY_USERS: ${WEAVIATE_API_USER:-dataflux-user}
    volumes:
      - weaviate_data:/var/lib/weaviate
    ports:
      - "${WEAVIATE_PORT:-8080}:8080"
      - "${WEAVIATE_GRPC_PORT:-50051}:50051"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
    networks:
      - dataflux-network

  neo4j:
    image: neo4j:5.15-community
    container_name: dataflux-neo4j
    hostname: neo4j
    restart: unless-stopped
    environment:
      <<: *common-variables
      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-dataflux_pass}
      NEO4J_dbms_memory_heap_initial__size: 512m
      NEO4J_dbms_memory_heap_max__size: 2G
      NEO4J_dbms_memory_pagecache_size: 512m
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_plugins:/plugins
    ports:
      - "${NEO4J_HTTP_PORT:-7474}:7474"
      - "${NEO4J_BOLT_PORT:-7687}:7687"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "cypher-shell", "-u", "${NEO4J_USER:-neo4j}", "-p", "${NEO4J_PASSWORD:-dataflux_pass}", "RETURN 1"]
    networks:
      - dataflux-network

  redis:
    image: redis:7.2-alpine
    container_name: dataflux-redis
    hostname: redis
    restart: unless-stopped
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD:-dataflux_pass}
      --maxmemory ${REDIS_MAX_MEMORY:-2gb}
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis_data:/data
    ports:
      - "${REDIS_PORT:-6379}:6379"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "redis-cli", "--raw", "ping"]
    networks:
      - dataflux-network

  # =================================
  # Message Queue & Streaming
  # =================================
  
  kafka:
    image: apache/kafka:3.7.0
    container_name: dataflux-kafka
    hostname: kafka
    restart: unless-stopped
    environment:
      <<: *common-variables
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093,EXTERNAL://0.0.0.0:9094
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,EXTERNAL://localhost:9094
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LOG_DIRS: /var/lib/kafka/data
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'true'
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_NUM_PARTITIONS: 3
    volumes:
      - kafka_data:/var/lib/kafka/data
      - ./scripts/create-topics.sh:/docker-entrypoint-initdb.d/create-topics.sh:ro
    ports:
      - "${KAFKA_PORT:-9092}:9092"
      - "${KAFKA_EXTERNAL_PORT:-9094}:9094"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
    networks:
      - dataflux-network

  # =================================
  # Object Storage
  # =================================
  
  minio:
    image: minio/minio:latest
    container_name: dataflux-minio
    hostname: minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      <<: *common-variables
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin123}
      MINIO_DEFAULT_BUCKETS: ${MINIO_BUCKETS:-dataflux-assets,dataflux-thumbnails,dataflux-proxies}
    volumes:
      - minio_data:/data
    ports:
      - "${MINIO_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "mc", "ready", "local"]
    networks:
      - dataflux-network

  # =================================
  # Analytics
  # =================================
  
  clickhouse:
    image: clickhouse/clickhouse-server:24.1-alpine
    container_name: dataflux-clickhouse
    hostname: clickhouse
    restart: unless-stopped
    environment:
      <<: *common-variables
      CLICKHOUSE_DB: ${CLICKHOUSE_DB:-dataflux_analytics}
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-dataflux_user}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-dataflux_pass}
      CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: 1
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - clickhouse_logs:/var/log/clickhouse-server
    ports:
      - "${CLICKHOUSE_HTTP_PORT:-8123}:8123"
      - "${CLICKHOUSE_NATIVE_PORT:-9000}:9000"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
    networks:
      - dataflux-network

  # =================================
  # DataFlux Services
  # =================================
  
  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    container_name: dataflux-api-gateway
    hostname: api-gateway
    restart: unless-stopped
    environment:
      <<: *common-variables
      UPSTREAM_INGESTION: ingestion-service:8001
      UPSTREAM_QUERY: query-service:8002
      UPSTREAM_ANALYSIS: analysis-service:8003
      UPSTREAM_MCP: mcp-server:8004
    volumes:
      - ./services/api-gateway/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./services/api-gateway/configs:/etc/nginx/conf.d:ro
    ports:
      - "${API_GATEWAY_PORT:-80}:80"
      - "${API_GATEWAY_SSL_PORT:-443}:443"
    depends_on:
      - ingestion-service
      - query-service
      - analysis-service
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "nginx", "-t"]
    networks:
      - dataflux-network

  ingestion-service:
    build:
      context: ./services/ingestion-service
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: dataflux-ingestion
    hostname: ingestion-service
    restart: unless-stopped
    environment:
      <<: *common-variables
      SERVICE_NAME: ingestion-service
      DATABASE_URL: postgresql://${POSTGRES_USER:-dataflux_user}:${POSTGRES_PASSWORD:-dataflux_pass}@postgres:5432/${POSTGRES_DB:-dataflux}
      REDIS_URL: redis://default:${REDIS_PASSWORD:-dataflux_pass}@redis:6379/0
      KAFKA_BROKERS: kafka:9092
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin123}
    volumes:
      - ./services/ingestion-service:/app
      - ingestion_temp:/tmp/ingestion
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    networks:
      - dataflux-network

  analysis-service:
    build:
      context: ./services/analysis-service
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: dataflux-analysis
    hostname: analysis-service
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      <<: *common-variables
      SERVICE_NAME: analysis-service
      DATABASE_URL: postgresql://${POSTGRES_USER:-dataflux_user}:${POSTGRES_PASSWORD:-dataflux_pass}@postgres:5432/${POSTGRES_DB:-dataflux}
      WEAVIATE_URL: http://weaviate:8080
      WEAVIATE_API_KEY: ${WEAVIATE_API_KEY:-dataflux-key}
      KAFKA_BROKERS: kafka:9092
      KAFKA_CONSUMER_GROUP: analysis-consumers
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin123}
      MODEL_CACHE_DIR: /models
    volumes:
      - ./services/analysis-service:/app
      - model_cache:/models
      - analysis_temp:/tmp/analysis
    depends_on:
      postgres:
        condition: service_healthy
      weaviate:
        condition: service_healthy
      kafka:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
    networks:
      - dataflux-network

  query-service:
    build:
      context: ./services/query-service
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: dataflux-query
    hostname: query-service
    restart: unless-stopped
    environment:
      <<: *common-variables
      SERVICE_NAME: query-service
      DATABASE_URL: postgresql://${POSTGRES_USER:-dataflux_user}:${POSTGRES_PASSWORD:-dataflux_pass}@postgres:5432/${POSTGRES_DB:-dataflux}
      WEAVIATE_URL: http://weaviate:8080
      WEAVIATE_API_KEY: ${WEAVIATE_API_KEY:-dataflux-key}
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USER:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-dataflux_pass}
      REDIS_URL: redis://default:${REDIS_PASSWORD:-dataflux_pass}@redis:6379/0
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-dataflux_user}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-dataflux_pass}
    volumes:
      - ./services/query-service:/app
    depends_on:
      postgres:
        condition: service_healthy
      weaviate:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
    networks:
      - dataflux-network

  mcp-server:
    build:
      context: ./services/mcp-server
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: dataflux-mcp
    hostname: mcp-server
    restart: unless-stopped
    environment:
      <<: *common-variables
      SERVICE_NAME: mcp-server
      MCP_SERVER_NAME: dataflux-mcp
      MCP_SERVER_VERSION: 1.0.0
      QUERY_SERVICE_URL: http://query-service:8002
      INGESTION_SERVICE_URL: http://ingestion-service:8001
      REDIS_URL: redis://default:${REDIS_PASSWORD:-dataflux_pass}@redis:6379/0
    volumes:
      - ./services/mcp-server:/app
      - ./services/mcp-server/node_modules:/app/node_modules
    depends_on:
      query-service:
        condition: service_healthy
      ingestion-service:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
    ports:
      - "${MCP_PORT:-8004}:8004"
      - "${MCP_SSE_PORT:-8005}:8005"
    networks:
      - dataflux-network

  # =================================
  # Development Tools
  # =================================
  
  pgadmin:
    profiles: ["dev", "tools"]
    image: dpage/pgadmin4:latest
    container_name: dataflux-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL:-admin@dataflux.local}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:-admin}
      PGADMIN_CONFIG_SERVER_MODE: 'False'
    volumes:
      - pgadmin_data:/var/lib/pgadmin
      - ./scripts/pgadmin/servers.json:/pgadmin4/servers.json:ro
    ports:
      - "${PGADMIN_PORT:-5050}:80"
    depends_on:
      - postgres
    networks:
      - dataflux-network

  kafka-ui:
    profiles: ["dev", "tools"]
    image: provectuslabs/kafka-ui:latest
    container_name: dataflux-kafka-ui
    environment:
      KAFKA_CLUSTERS_0_NAME: dataflux
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
      DYNAMIC_CONFIG_ENABLED: 'true'
    ports:
      - "${KAFKA_UI_PORT:-8090}:8080"
    depends_on:
      - kafka
    networks:
      - dataflux-network

  redis-commander:
    profiles: ["dev", "tools"]
    image: rediscommander/redis-commander:latest
    container_name: dataflux-redis-commander
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD:-dataflux_pass}
    ports:
      - "${REDIS_COMMANDER_PORT:-8081}:8081"
    depends_on:
      - redis
    networks:
      - dataflux-network

volumes:
  postgres_data:
  weaviate_data:
  neo4j_data:
  neo4j_logs:
  neo4j_plugins:
  redis_data:
  kafka_data:
  minio_data:
  clickhouse_data:
  clickhouse_logs:
  pgadmin_data:
  model_cache:
  ingestion_temp:
  analysis_temp:

networks:
  dataflux-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 2.2 Environment Variables (.env.example)

```bash
# General Settings
TZ=Europe/Berlin
ENVIRONMENT=development
LOG_LEVEL=info
BUILD_TARGET=development

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=dataflux
POSTGRES_USER=dataflux_user
POSTGRES_PASSWORD=secure_password_here

# Weaviate
WEAVIATE_PORT=8080
WEAVIATE_GRPC_PORT=50051
WEAVIATE_API_KEY=your_weaviate_api_key_here
WEAVIATE_API_USER=dataflux_user

# Neo4j
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_neo4j_password_here

# Redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password_here
REDIS_MAX_MEMORY=2gb

# Kafka
KAFKA_PORT=9092
KAFKA_EXTERNAL_PORT=9094

# MinIO
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=secure_minio_password_here
MINIO_BUCKETS=dataflux-assets,dataflux-thumbnails,dataflux-proxies

# ClickHouse
CLICKHOUSE_HTTP_PORT=8123
CLICKHOUSE_NATIVE_PORT=9000
CLICKHOUSE_DB=dataflux_analytics
CLICKHOUSE_USER=dataflux_user
CLICKHOUSE_PASSWORD=secure_clickhouse_password_here

# API Gateway
API_GATEWAY_PORT=80
API_GATEWAY_SSL_PORT=443

# MCP Server
MCP_PORT=8004
MCP_SSE_PORT=8005

# Development Tools
PGADMIN_PORT=5050
PGADMIN_EMAIL=admin@dataflux.local
PGADMIN_PASSWORD=admin
KAFKA_UI_PORT=8090
REDIS_COMMANDER_PORT=8081

# OpenAI / AI Models
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 3. Service Implementierungen

### 3.1 Ingestion Service (Python/FastAPI)

```python
# services/ingestion-service/src/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import hashlib
import asyncpg
import aioredis
import aiokafka
from minio import Minio
import magic
from datetime import datetime
import uuid
import json

app = FastAPI(
    title="DataFlux Ingestion Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class AssetUpload(BaseModel):
    context: Optional[str] = Field(None, description="User-provided context")
    priority: int = Field(5, ge=1, le=10, description="Processing priority")
    collection_id: Optional[str] = Field(None, description="Collection UUID")

class AssetResponse(BaseModel):
    id: str
    filename: str
    file_hash: str
    status: str
    created_at: datetime
    processing_eta: Optional[int]

# Dependencies
async def get_db():
    conn = await asyncpg.connect(
        host=os.getenv("DATABASE_HOST"),
        database=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD")
    )
    try:
        yield conn
    finally:
        await conn.close()

async def get_redis():
    redis = await aioredis.create_redis_pool(
        os.getenv("REDIS_URL"),
        encoding="utf-8"
    )
    try:
        yield redis
    finally:
        redis.close()
        await redis.wait_closed()

async def get_kafka_producer():
    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS"),
        value_serializer=lambda v: json.dumps(v).encode()
    )
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

# Endpoints
@app.post("/api/v1/assets", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    metadata: AssetUpload = Depends(),
    db: asyncpg.Connection = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    kafka: aiokafka.AIOKafkaProducer = Depends(get_kafka_producer)
):
    """Upload and queue an asset for processing"""
    
    # Calculate file hash
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicates
    existing = await db.fetchval(
        "SELECT id FROM assets WHERE file_hash = $1",
        file_hash
    )
    if existing:
        raise HTTPException(status_code=409, detail="Asset already exists")
    
    # Detect MIME type
    mime_type = magic.from_buffer(content, mime=True)
    
    # Generate UUID
    asset_id = str(uuid.uuid4())
    
    # Store in MinIO
    minio_client = Minio(
        os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=False
    )
    
    bucket = "dataflux-assets"
    object_name = f"{asset_id}/{file.filename}"
    
    minio_client.put_object(
        bucket,
        object_name,
        io.BytesIO(content),
        len(content),
        content_type=mime_type
    )
    
    # Store metadata in PostgreSQL
    await db.execute("""
        INSERT INTO assets (
            id, filename, file_hash, file_size, mime_type,
            storage_path, upload_context, processing_status,
            processing_priority, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    """, asset_id, file.filename, file_hash, len(content),
        mime_type, object_name, metadata.context, "queued",
        metadata.priority, datetime.utcnow())
    
    # Send to Kafka queue
    await kafka.send_and_wait(
        "asset-processing",
        {
            "asset_id": asset_id,
            "mime_type": mime_type,
            "priority": metadata.priority,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Cache in Redis
    await redis.setex(
        f"asset:{asset_id}",
        3600,  # 1 hour TTL
        json.dumps({
            "status": "queued",
            "filename": file.filename
        })
    )
    
    return AssetResponse(
        id=asset_id,
        filename=file.filename,
        file_hash=file_hash,
        status="queued",
        created_at=datetime.utcnow(),
        processing_eta=calculate_eta(len(content), metadata.priority)
    )

@app.get("/api/v1/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get asset details"""
    asset = await db.fetchrow(
        "SELECT * FROM assets WHERE id = $1",
        asset_id
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return dict(asset)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ingestion"}
```

### 3.2 Query Service (Go/Gin)

```go
// services/query-service/cmd/main.go
package main

import (
    "context"
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/go-redis/redis/v8"
    "github.com/jackc/pgx/v4/pgxpool"
    "github.com/neo4j/neo4j-go-driver/v4/neo4j"
    "github.com/weaviate/weaviate-go-client/v2/weaviate"
)

type SearchRequest struct {
    Query       string                 `json:"query" binding:"required"`
    MediaTypes  []string              `json:"media_types"`
    Filters     map[string]interface{} `json:"filters"`
    Limit       int                   `json:"limit"`
    Offset      int                   `json:"offset"`
    IncludeSegments bool              `json:"include_segments"`
}

type SearchResponse struct {
    Results []SearchResult `json:"results"`
    Total   int           `json:"total"`
    Took    int64         `json:"took_ms"`
}

type SearchResult struct {
    ID         string                 `json:"id"`
    Type       string                 `json:"type"`
    Score      float64               `json:"score"`
    Metadata   map[string]interface{} `json:"metadata"`
    Segments   []Segment             `json:"segments,omitempty"`
    Highlights []string              `json:"highlights,omitempty"`
}

type Segment struct {
    ID         string    `json:"id"`
    StartTime  float64   `json:"start_time,omitempty"`
    EndTime    float64   `json:"end_time,omitempty"`
    Confidence float64   `json:"confidence"`
    Features   map[string]interface{} `json:"features"`
}

var (
    db          *pgxpool.Pool
    redisClient *redis.Client
    neo4jDriver neo4j.Driver
    weaviateClient *weaviate.Client
)

func main() {
    initConnections()
    defer closeConnections()

    router := gin.Default()
    
    // Middleware
    router.Use(CORSMiddleware())
    router.Use(gin.Recovery())
    router.Use(RequestLogger())
    
    // Routes
    v1 := router.Group("/api/v1")
    {
        v1.POST("/search", handleSearch)
        v1.POST("/similar", handleSimilar)
        v1.GET("/segments/:id", handleGetSegment)
        v1.GET("/relationships", handleGetRelationships)
    }
    
    router.GET("/health", handleHealth)
    
    port := os.Getenv("PORT")
    if port == "" {
        port = "8002"
    }
    
    log.Printf("Query Service starting on port %s", port)
    router.Run(":" + port)
}

func handleSearch(c *gin.Context) {
    start := time.Now()
    
    var req SearchRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    
    // Check Redis cache
    cacheKey := generateCacheKey(req)
    cached, err := redisClient.Get(context.Background(), cacheKey).Result()
    if err == nil {
        var response SearchResponse
        json.Unmarshal([]byte(cached), &response)
        c.JSON(200, response)
        return
    }
    
    // Parse query for NLP
    nlpResult := parseNaturalLanguageQuery(req.Query)
    
    // Build multi-index query
    var results []SearchResult
    
    // 1. Vector search in Weaviate
    if nlpResult.HasSemanticIntent {
        vectorResults := searchWeaviate(nlpResult, req.Filters, req.Limit)
        results = append(results, vectorResults...)
    }
    
    // 2. Full-text search in PostgreSQL
    if nlpResult.HasKeywords {
        textResults := searchPostgreSQL(nlpResult.Keywords, req.Filters, req.Limit)
        results = append(results, textResults...)
    }
    
    // 3. Graph traversal in Neo4j
    if nlpResult.HasRelationships {
        graphResults := searchNeo4j(nlpResult.Relationships, req.Limit)
        results = append(results, graphResults...)
    }
    
    // Merge and rank results
    rankedResults := rankResults(results, req.Query)
    
    // Include segments if requested
    if req.IncludeSegments {
        enrichWithSegments(rankedResults)
    }
    
    response := SearchResponse{
        Results: rankedResults,
        Total:   len(rankedResults),
        Took:    time.Since(start).Milliseconds(),
    }
    
    // Cache results
    cacheData, _ := json.Marshal(response)
    redisClient.SetEX(context.Background(), cacheKey, string(cacheData), 5*time.Minute)
    
    c.JSON(200, response)
}

func searchWeaviate(nlp NLPResult, filters map[string]interface{}, limit int) []SearchResult {
    ctx := context.Background()
    
    className := "MediaSegment"
    nearText := weaviateClient.GraphQL().NearTextArgBuilder().
        WithConcepts([]string{nlp.Query})
    
    fields := []graphql.Field{
        {Name: "id"},
        {Name: "type"},
        {Name: "_additional", Fields: []graphql.Field{
            {Name: "certainty"},
            {Name: "distance"},
        }},
        {Name: "metadata"},
    }
    
    result, err := weaviateClient.GraphQL().Get().
        WithClassName(className).
        WithNearText(nearText).
        WithFields(fields...).
        WithLimit(limit).
        Do(ctx)
    
    if err != nil {
        log.Printf("Weaviate search error: %v", err)
        return []SearchResult{}
    }
    
    return parseWeaviateResults(result)
}

func handleHealth(c *gin.Context) {
    health := gin.H{
        "status": "healthy",
        "service": "query-service",
        "connections": gin.H{
            "postgres": checkPostgres(),
            "redis": checkRedis(),
            "neo4j": checkNeo4j(),
            "weaviate": checkWeaviate(),
        },
    }
    c.JSON(200, health)
}
```

### 3.3 MCP Server (TypeScript)

```typescript
// services/mcp-server/src/index.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express from "express";
import { z } from "zod";
import axios from "axios";
import Redis from "ioredis";

// Initialize MCP Server
const server = new McpServer({
  name: "dataflux-mcp",
  version: "1.0.0",
  description: "DataFlux MCP Server for media content management"
});

// Initialize Redis client
const redis = new Redis({
  host: process.env.REDIS_HOST || "redis",
  port: parseInt(process.env.REDIS_PORT || "6379"),
  password: process.env.REDIS_PASSWORD
});

// Tool Schemas
const searchSchema = z.object({
  query: z.string().describe("Natural language search query"),
  media_type: z.enum(["video", "image", "audio", "document", "all"]).optional(),
  confidence_threshold: z.number().min(0).max(1).optional().default(0.7),
  limit: z.number().min(1).max(100).optional().default(20)
});

const analyzeSchema = z.object({
  file_path: z.string().describe("Path to the file to analyze"),
  context: z.string().optional().describe("Additional context about the file"),
  priority: z.enum(["high", "medium", "low"]).optional().default("medium")
});

const getSimilarSchema = z.object({
  entity_id: z.string().describe("ID of the entity to find similar items for"),
  threshold: z.number().min(0).max(1).optional().default(0.75),
  limit: z.number().min(1).max(50).optional().default(10)
});

// Register Tools
server.registerTool(
  "dataflux_search",
  {
    title: "Search DataFlux",
    description: "Search for media content using natural language",
    inputSchema: searchSchema
  },
  async (input) => {
    const { query, media_type, confidence_threshold, limit } = input;
    
    try {
      // Call Query Service
      const response = await axios.post(
        `${process.env.QUERY_SERVICE_URL}/api/v1/search`,
        {
          query,
          media_types: media_type === "all" ? [] : [media_type],
          limit,
          filters: { confidence_min: confidence_threshold }
        }
      );
      
      const results = response.data.results;
      
      // Format results for LLM
      const formatted = results.map((r: any) => ({
        type: r.type,
        score: r.score,
        description: r.metadata.description || "No description",
        location: r.metadata.storage_path,
        segments: r.segments?.length || 0
      }));
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify(formatted, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error searching DataFlux: ${error.message}`
        }],
        isError: true
      };
    }
  }
);

server.registerTool(
  "dataflux_analyze",
  {
    title: "Analyze Content",
    description: "Queue content for AI analysis and indexing",
    inputSchema: analyzeSchema
  },
  async (input) => {
    const { file_path, context, priority } = input;
    
    const priorityMap = { high: 2, medium: 5, low: 8 };
    
    try {
      // Upload to Ingestion Service
      const formData = new FormData();
      // In production, you'd read the actual file
      // formData.append("file", fileBuffer);
      formData.append("metadata", JSON.stringify({
        context,
        priority: priorityMap[priority]
      }));
      
      const response = await axios.post(
        `${process.env.INGESTION_SERVICE_URL}/api/v1/assets`,
        formData
      );
      
      return {
        content: [{
          type: "text",
          text: `Asset queued for analysis:\n- ID: ${response.data.id}\n- Status: ${response.data.status}\n- ETA: ${response.data.processing_eta} seconds`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error analyzing content: ${error.message}`
        }],
        isError: true
      };
    }
  }
);

server.registerTool(
  "dataflux_similar",
  {
    title: "Find Similar Content",
    description: "Find content similar to a given entity",
    inputSchema: getSimilarSchema
  },
  async (input) => {
    const { entity_id, threshold, limit } = input;
    
    try {
      const response = await axios.post(
        `${process.env.QUERY_SERVICE_URL}/api/v1/similar`,
        { entity_id, threshold, limit }
      );
      
      return {
        content: [{
          type: "text",
          text: `Found ${response.data.results.length} similar items:\n${
            response.data.results.map((r: any) => 
              `- ${r.type}: ${r.metadata.filename} (similarity: ${r.score})`
            ).join('\n')
          }`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error finding similar content: ${error.message}`
        }],
        isError: true
      };
    }
  }
);

// Register Resources
server.registerResource(
  "statistics",
  {
    title: "DataFlux Statistics",
    description: "Get current system statistics"
  },
  async () => {
    const stats = await redis.hgetall("dataflux:stats");
    
    return {
      contents: [{
        uri: "dataflux://statistics",
        mimeType: "application/json",
        text: JSON.stringify({
          total_assets: stats.total_assets || 0,
          total_segments: stats.total_segments || 0,
          processing_queue: stats.processing_queue || 0,
          last_updated: new Date().toISOString()
        }, null, 2)
      }]
    };
  }
);

// Register Prompts
server.registerPrompt(
  "analyze_video",
  {
    title: "Analyze Video Content",
    description: "Comprehensive video analysis prompt"
  },
  async () => ({
    messages: [{
      role: "user",
      content: {
        type: "text",
        text: `Analyze this video for the following aspects:
1. Visual content (objects, people, scenes)
2. Audio content (speech, music, effects)
3. Technical quality (resolution, frame rate, encoding)
4. Semantic meaning (story, message, emotion)
5. Style and aesthetics (cinematography, color grading)

Provide confidence scores for each aspect.`
      }
    }]
  })
);

// Setup Express app for SSE transport
const app = express();
app.use(express.json());

// SSE endpoint
const sseTransport = new SSEServerTransport("/sse", response => response);
server.connect(sseTransport);

app.post("/sse", sseTransport.handleRequest);

// Health check
app.get("/health", (req, res) => {
  res.json({ 
    status: "healthy", 
    service: "mcp-server",
    tools: server.getTools().length,
    resources: server.getResources().length
  });
});

// Start servers
const PORT = process.env.MCP_PORT || 8004;
const SSE_PORT = process.env.MCP_SSE_PORT || 8005;

// HTTP/SSE Server
app.listen(SSE_PORT, () => {
  console.log(`MCP SSE Server running on port ${SSE_PORT}`);
});

// STDIO Server for local development
if (process.env.ENABLE_STDIO === "true") {
  const transport = new StdioServerTransport();
  server.connect(transport).then(() => {
    console.log("MCP STDIO Server started");
  });
}

// Graceful shutdown
process.on("SIGTERM", async () => {
  console.log("Shutting down MCP server...");
  await redis.quit();
  process.exit(0);
});
```

## 4. API Spezifikation (OpenAPI 3.0)

```yaml
# docs/api/openapi.yaml
openapi: 3.0.0
info:
  title: DataFlux API
  version: 1.0.0
  description: Universal AI-native database for media content

servers:
  - url: http://localhost/api/v1
    description: Development server
  - url: https://api.dataflux.io/v1
    description: Production server

paths:
  /assets:
    post:
      summary: Upload a new asset
      tags:
        - Assets
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                context:
                  type: string
                  description: User-provided context
                priority:
                  type: integer
                  minimum: 1
                  maximum: 10
                  default: 5
                collection_id:
                  type: string
                  format: uuid
      responses:
        '201':
          description: Asset uploaded successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetResponse'
        '409':
          description: Asset already exists

    get:
      summary: List assets
      tags:
        - Assets
      parameters:
        - in: query
          name: page
          schema:
            type: integer
            default: 1
        - in: query
          name: limit
          schema:
            type: integer
            default: 20
            maximum: 100
        - in: query
          name: status
          schema:
            type: string
            enum: [queued, processing, completed, failed]
        - in: query
          name: mime_type
          schema:
            type: string
      responses:
        '200':
          description: List of assets
          content:
            application/json:
              schema:
                type: object
                properties:
                  assets:
                    type: array
                    items:
                      $ref: '#/components/schemas/Asset'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

  /assets/{id}:
    get:
      summary: Get asset details
      tags:
        - Assets
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Asset details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetDetail'
        '404':
          description: Asset not found

    delete:
      summary: Delete an asset
      tags:
        - Assets
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Asset deleted
        '404':
          description: Asset not found

  /assets/{id}/analyze:
    post:
      summary: Trigger re-analysis of an asset
      tags:
        - Assets
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                force:
                  type: boolean
                  default: false
                priority:
                  type: integer
                  minimum: 1
                  maximum: 10
      responses:
        '202':
          description: Analysis queued
        '404':
          description: Asset not found

  /search:
    post:
      summary: Search for content
      tags:
        - Search
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchRequest'
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'

  /similar:
    post:
      summary: Find similar content
      tags:
        - Search
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required:
                - entity_id
              properties:
                entity_id:
                  type: string
                  format: uuid
                threshold:
                  type: number
                  minimum: 0
                  maximum: 1
                  default: 0.75
                limit:
                  type: integer
                  minimum: 1
                  maximum: 50
                  default: 10
                media_types:
                  type: array
                  items:
                    type: string
      responses:
        '200':
          description: Similar content found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'

  /segments/{id}:
    get:
      summary: Get segment details
      tags:
        - Segments
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Segment details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Segment'
        '404':
          description: Segment not found

  /collections:
    get:
      summary: List collections
      tags:
        - Collections
      responses:
        '200':
          description: List of collections
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Collection'

    post:
      summary: Create a collection
      tags:
        - Collections
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required:
                - name
              properties:
                name:
                  type: string
                description:
                  type: string
                auto_generated:
                  type: boolean
                  default: false
      responses:
        '201':
          description: Collection created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Collection'

  /feedback:
    post:
      summary: Submit feedback
      tags:
        - System
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required:
                - type
                - entity_id
                - feedback
              properties:
                type:
                  type: string
                  enum: [relevance, accuracy, quality]
                entity_id:
                  type: string
                  format: uuid
                feedback:
                  type: boolean
                details:
                  type: string
      responses:
        '201':
          description: Feedback recorded

components:
  schemas:
    Asset:
      type: object
      properties:
        id:
          type: string
          format: uuid
        filename:
          type: string
        file_hash:
          type: string
        file_size:
          type: integer
        mime_type:
          type: string
        status:
          type: string
          enum: [queued, processing, completed, failed]
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    AssetDetail:
      allOf:
        - $ref: '#/components/schemas/Asset'
        - type: object
          properties:
            storage_path:
              type: string
            proxy_path:
              type: string
            thumbnail_path:
              type: string
            processing_status:
              type: string
            confidence_score:
              type: number
            segments:
              type: array
              items:
                $ref: '#/components/schemas/Segment'
            metadata:
              type: object

    Segment:
      type: object
      properties:
        id:
          type: string
          format: uuid
        asset_id:
          type: string
          format: uuid
        segment_type:
          type: string
        sequence_number:
          type: integer
        start_time:
          type: number
        end_time:
          type: number
        duration:
          type: number
        confidence_score:
          type: number
        visual_features:
          type: object
        semantic_features:
          type: object
        style_features:
          type: object
        technical_features:
          type: object
        audio_features:
          type: object

    SearchRequest:
      type: object
      required:
        - query
      properties:
        query:
          type: string
        media_types:
          type: array
          items:
            type: string
        filters:
          type: object
        limit:
          type: integer
          default: 20
        offset:
          type: integer
          default: 0
        include_segments:
          type: boolean
          default: false

    SearchResponse:
      type: object
      properties:
        results:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                format: uuid
              type:
                type: string
              score:
                type: number
              metadata:
                type: object
              segments:
                type: array
                items:
                  $ref: '#/components/schemas/Segment'
              highlights:
                type: array
                items:
                  type: string
        total:
          type: integer
        took_ms:
          type: integer

    Collection:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        asset_count:
          type: integer
        auto_generated:
          type: boolean
        created_at:
          type: string
          format: date-time

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        pages:
          type: integer
```

## 5. Makefile für Development

```makefile
# DataFlux Makefile

.PHONY: help
help:
	@echo "DataFlux Development Commands"
	@echo "=============================="
	@echo "make setup       - Initial setup"
	@echo "make dev         - Start development environment"
	@echo "make dev-tools   - Start with development tools"
	@echo "make stop        - Stop all services"
	@echo "make clean       - Clean up volumes and containers"
	@echo "make logs        - Show logs"
	@echo "make test        - Run tests"
	@echo "make build       - Build all services"
	@echo "make migrate     - Run database migrations"

.PHONY: setup
setup:
	@echo "Setting up DataFlux development environment..."
	cp docker/.env.example docker/.env
	@echo "Please edit docker/.env with your configuration"
	docker network create dataflux-network 2>/dev/null || true
	make build
	make migrate

.PHONY: dev
dev:
	cd docker && docker-compose up -d
	@echo "DataFlux is running!"
	@echo "API Gateway: http://localhost"
	@echo "API Docs: http://localhost/docs"

.PHONY: dev-tools
dev-tools:
	cd docker && docker-compose --profile dev --profile tools up -d
	@echo "Development tools are running!"
	@echo "PgAdmin: http://localhost:5050"
	@echo "Kafka UI: http://localhost:8090"
	@echo "Redis Commander: http://localhost:8081"
	@echo "MinIO Console: http://localhost:9001"

.PHONY: stop
stop:
	cd docker && docker-compose stop

.PHONY: clean
clean:
	cd docker && docker-compose down -v
	docker network rm dataflux-network 2>/dev/null || true

.PHONY: logs
logs:
	cd docker && docker-compose logs -f

.PHONY: logs-service
logs-service:
	cd docker && docker-compose logs -f $(SERVICE)

.PHONY: test
test:
	@echo "Running tests..."
	cd services/ingestion-service && python -m pytest
	cd services/query-service && go test ./...
	cd services/mcp-server && npm test

.PHONY: build
build:
	cd docker && docker-compose build

.PHONY: migrate
migrate:
	cd docker && docker-compose run --rm postgres psql -h postgres -U dataflux_user -d dataflux -f /docker-entrypoint-initdb.d/01-init.sql

.PHONY: shell
shell:
	cd docker && docker-compose exec $(SERVICE) /bin/sh

.PHONY: psql
psql:
	cd docker && docker-compose exec postgres psql -U dataflux_user -d dataflux

.PHONY: redis-cli
redis-cli:
	cd docker && docker-compose exec redis redis-cli -a dataflux_pass
```

## 6. Entwicklungs-Workflow

### 6.1 Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/dataflux.git
cd dataflux

# Setup environment
make setup

# Start services
make dev

# With development tools
make dev-tools
```

### 6.2 Service Development

```bash
# Entwicklung am Ingestion Service
cd services/ingestion-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001

# Entwicklung am Query Service
cd services/query-service
go mod download
go run cmd/main.go

# Entwicklung am MCP Server
cd services/mcp-server
npm install
npm run dev
```

### 6.3 Testing

```bash
# Unit Tests
make test

# Integration Tests
docker-compose -f docker/docker-compose.test.yml up --abort-on-container-exit

# API Tests
curl -X POST http://localhost/api/v1/assets \
  -F "file=@sample.mp4" \
  -F "context=Test video"

# MCP Server Test
npx @modelcontextprotocol/inspector services/mcp-server/build/index.js
```

## 7. Production Deployment

### 7.1 Docker Compose Production

```yaml
# docker/docker-compose.prod.yml
version: '3.9'

services:
  # Override development settings
  ingestion-service:
    build:
      target: production
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G

  analysis-service:
    build:
      target: production
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  query-service:
    build:
      target: production
    restart: always
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 7.2 Kubernetes Deployment

```yaml
# k8s/dataflux-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataflux-query-service
  namespace: dataflux
spec:
  replicas: 3
  selector:
    matchLabels:
      app: query-service
  template:
    metadata:
      labels:
        app: query-service
    spec:
      containers:
      - name: query-service
        image: dataflux/query-service:latest
        ports:
        - containerPort: 8002
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dataflux-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: dataflux-secrets
              key: redis-url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: query-service
  namespace: dataflux
spec:
  selector:
    app: query-service
  ports:
    - protocol: TCP
      port: 8002
      targetPort: 8002
  type: ClusterIP
```

## 8. Monitoring & Observability

### 8.1 Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dataflux-services'
    static_configs:
      - targets:
        - 'ingestion-service:8001'
        - 'query-service:8002'
        - 'analysis-service:8003'
        - 'mcp-server:8004'
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 8.2 Grafana Dashboards

```json
// monitoring/dashboards/dataflux-overview.json
{
  "dashboard": {
    "title": "DataFlux Overview",
    "panels": [
      {
        "title": "Asset Processing Rate",
        "targets": [
          {
            "expr": "rate(dataflux_assets_processed_total[5m])"
          }
        ]
      },
      {
        "title": "Query Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(dataflux_query_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Analysis Queue Depth",
        "targets": [
          {
            "expr": "dataflux_analysis_queue_size"
          }
        ]
      },
      {
        "title": "Storage Usage",
        "targets": [
          {
            "expr": "dataflux_storage_bytes_used / dataflux_storage_bytes_total * 100"
          }
        ]
      }
    ]
  }
}
```

## 9. Security Configuration

### 9.1 SSL/TLS Setup

```nginx
# services/api-gateway/configs/ssl.conf
server {
    listen 443 ssl http2;
    server_name api.dataflux.local;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    location / {
        proxy_pass http://upstream_services;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 9.2 Authentication Middleware

```python
# services/shared/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import os

security = HTTPBearer()

class AuthHandler:
    secret = os.getenv("JWT_SECRET", "your-secret-key")
    algorithm = "HS256"
    
    def encode_token(self, user_id: str, permissions: list = None):
        payload = {
            "exp": datetime.utcnow() + timedelta(days=1),
            "iat": datetime.utcnow(),
            "sub": user_id,
            "permissions": permissions or []
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload["sub"], payload.get("permissions", [])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

auth_handler = AuthHandler()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id, permissions = auth_handler.decode_token(token)
    return {"user_id": user_id, "permissions": permissions}

def require_permission(permission: str):
    async def permission_checker(user=Depends(get_current_user)):
        if permission not in user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return permission_checker
```

## 10. CI/CD Pipeline

### 10.1 GitHub Actions Workflow

```yaml
# .github/workflows/dataflux-ci-cd.yml
name: DataFlux CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd services/ingestion-service && pip install -r requirements.txt
          cd ../query-service && go mod download
          cd ../mcp-server && npm ci
      
      - name: Run tests
        run: |
          cd services/ingestion-service && pytest
          cd ../query-service && go test ./...
          cd ../mcp-server && npm test
      
      - name: Run linters
        run: |
          cd services/ingestion-service && pylint src/
          cd ../query-service && golangci-lint run
          cd ../mcp-server && npm run lint

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    strategy:
      matrix:
        service:
          - ingestion-service
          - analysis-service
          - query-service
          - mcp-server
          - api-gateway

    steps:
      - uses: actions/checkout@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/${{ matrix.service }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: ./services/${{ matrix.service }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Kubernetes
        run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          kubectl apply -f k8s/
          kubectl rollout status deployment/dataflux-query-service -n dataflux
```

## 11. Backup & Recovery

### 11.1 Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting DataFlux backup..."

# PostgreSQL backup
echo "Backing up PostgreSQL..."
docker-compose exec -T postgres pg_dump -U dataflux_user dataflux | gzip > "$BACKUP_DIR/postgres.sql.gz"

# Neo4j backup
echo "Backing up Neo4j..."
docker-compose exec -T neo4j neo4j-admin backup --database=neo4j --to="/backup/neo4j.backup"
docker cp dataflux-neo4j:/backup/neo4j.backup "$BACKUP_DIR/"

# MinIO backup
echo "Backing up MinIO..."
docker-compose exec -T minio mc mirror --overwrite minio/dataflux-assets "$BACKUP_DIR/minio/"

# Redis backup
echo "Backing up Redis..."
docker-compose exec -T redis redis-cli --rdb /data/dump.rdb BGSAVE
sleep 5
docker cp dataflux-redis:/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# Weaviate backup
echo "Backing up Weaviate..."
curl -X POST "http://localhost:8080/v1/backups" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"backup-$(date +%Y%m%d)\", \"include\": [\"*\"]}"

echo "Backup completed: $BACKUP_DIR"
```

### 11.2 Recovery Script

```bash
#!/bin/bash
# scripts/restore.sh

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup-directory>"
    exit 1
fi

BACKUP_DIR="$1"

echo "Starting DataFlux recovery from $BACKUP_DIR..."

# PostgreSQL restore
echo "Restoring PostgreSQL..."
gunzip -c "$BACKUP_DIR/postgres.sql.gz" | docker-compose exec -T postgres psql -U dataflux_user dataflux

# Neo4j restore
echo "Restoring Neo4j..."
docker cp "$BACKUP_DIR/neo4j.backup" dataflux-neo4j:/backup/
docker-compose exec -T neo4j neo4j-admin restore --database=neo4j --from="/backup/neo4j.backup"

# MinIO restore
echo "Restoring MinIO..."
docker-compose exec -T minio mc cp --recursive "$BACKUP_DIR/minio/" minio/dataflux-assets/

# Redis restore
echo "Restoring Redis..."
docker cp "$BACKUP_DIR/redis.rdb" dataflux-redis:/data/dump.rdb
docker-compose restart redis

echo "Recovery completed!"
```

## 12. Performance Optimization

### 12.1 Database Indexes

```sql
-- scripts/optimize-db.sql

-- PostgreSQL Indexes
CREATE INDEX idx_assets_file_hash ON assets(file_hash);
CREATE INDEX idx_assets_mime_type ON assets(mime_type);
CREATE INDEX idx_assets_status ON assets(processing_status);
CREATE INDEX idx_assets_created ON assets(created_at DESC);

CREATE INDEX idx_segments_asset_id ON segments(asset_id);
CREATE INDEX idx_segments_confidence ON segments(confidence_score DESC);
CREATE INDEX idx_segments_type ON segments(segment_type);

CREATE INDEX idx_features_segment_id ON features(segment_id);
CREATE INDEX idx_features_domain_type ON features(feature_domain, feature_type);

-- Full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_assets_filename_trgm ON assets USING gin(filename gin_trgm_ops);

-- JSONB indexes
CREATE INDEX idx_segments_visual_features ON segments USING gin(visual_features);
CREATE INDEX idx_segments_semantic_features ON segments USING gin(semantic_features);
```

### 12.2 Caching Strategy

```typescript
// services/shared/cache.ts
import Redis from 'ioredis';
import { createHash } from 'crypto';

export class CacheManager {
  private redis: Redis;
  private defaultTTL = 300; // 5 minutes

  constructor(redisUrl: string) {
    this.redis = new Redis(redisUrl);
  }

  private generateKey(prefix: string, params: any): string {
    const hash = createHash('md5')
      .update(JSON.stringify(params))
      .digest('hex');
    return `${prefix}:${hash}`;
  }

  async get<T>(key: string): Promise<T | null> {
    const cached = await this.redis.get(key);
    if (!cached) return null;
    return JSON.parse(cached);
  }

  async set(key: string, value: any, ttl?: number): Promise<void> {
    await this.redis.setex(
      key,
      ttl || this.defaultTTL,
      JSON.stringify(value)
    );
  }

  async invalidate(pattern: string): Promise<void> {
    const keys = await this.redis.keys(pattern);
    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
  }

  async cacheQuery<T>(
    prefix: string,
    params: any,
    fetcher: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    const key = this.generateKey(prefix, params);
    
    // Try cache first
    const cached = await this.get<T>(key);
    if (cached) return cached;
    
    // Fetch and cache
    const result = await fetcher();
    await this.set(key, result, ttl);
    
    return result;
  }
}
```

## 13. Troubleshooting Guide

### 13.1 Common Issues

```markdown
# DataFlux Troubleshooting Guide

## Service Won't Start

### PostgreSQL Connection Error
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U dataflux_user
```

### Kafka Connection Issues
```bash
# Check Kafka health
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# List topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Create missing topics
docker-compose exec kafka kafka-topics --create \
  --topic asset-processing \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### Weaviate Connection Failed
```bash
# Check Weaviate status
curl http://localhost:8080/v1/.well-known/ready

# Check schema
curl http://localhost:8080/v1/schema
```

## Performance Issues

### Slow Queries
```sql
-- Check slow queries in PostgreSQL
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check missing indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
```

### High Memory Usage
```bash
# Check container memory usage
docker stats

# Limit memory in docker-compose
# Add to service definition:
deploy:
  resources:
    limits:
      memory: 2G
```

### Queue Backlog
```python
# Check Kafka consumer lag
from kafka import KafkaAdminClient

admin = KafkaAdminClient(bootstrap_servers='localhost:9092')
consumer_groups = admin.list_consumer_groups()

for group in consumer_groups:
    lag = admin.list_consumer_group_offsets(group)
    print(f"Group {group}: {lag}")
```

## Data Issues

### Duplicate Assets
```sql
-- Find duplicates
SELECT file_hash, COUNT(*)
FROM assets
GROUP BY file_hash
HAVING COUNT(*) > 1;

-- Remove duplicates (keep oldest)
DELETE FROM assets a1
WHERE EXISTS (
    SELECT 1
    FROM assets a2
    WHERE a2.file_hash = a1.file_hash
    AND a2.created_at < a1.created_at
);
```

### Orphaned Segments
```sql
-- Find orphaned segments
SELECT s.* FROM segments s
LEFT JOIN assets a ON s.asset_id = a.id
WHERE a.id IS NULL;

-- Clean up
DELETE FROM segments
WHERE asset_id NOT IN (SELECT id FROM assets);
```
```

## 14. Development Best Practices

### 14.1 Code Style Guidelines

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100']

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0
    hooks:
      - id: prettier
        files: \.(js|ts|jsx|tsx|json|yml|yaml|md)$
```

### 14.2 Testing Strategy

```python
# tests/test_ingestion.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import io

from services.ingestion_service.src.main import app

client = TestClient(app)

@pytest.fixture
def mock_dependencies():
    with patch('services.ingestion_service.src.main.get_db') as mock_db, \
         patch('services.ingestion_service.src.main.get_redis') as mock_redis, \
         patch('services.ingestion_service.src.main.get_kafka_producer') as mock_kafka:
        
        mock_db.return_value = Mock()
        mock_redis.return_value = Mock()
        mock_kafka.return_value = Mock()
        
        yield {
            'db': mock_db,
            'redis': mock_redis,
            'kafka': mock_kafka
        }

def test_upload_asset(mock_dependencies):
    # Prepare test file
    test_file = io.BytesIO(b"test content")
    test_file.name = "test.mp4"
    
    response = client.post(
        "/api/v1/assets",
        files={"file": ("test.mp4", test_file, "video/mp4")},
        data={"context": "Test video", "priority": 5}
    )
    
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["filename"] == "test.mp4"

def test_duplicate_detection(mock_dependencies):
    # Upload same file twice
    test_file = io.BytesIO(b"duplicate content")
    
    # First upload
    response1 = client.post(
        "/api/v1/assets",
        files={"file": ("test.mp4", test_file, "video/mp4")}
    )
    assert response1.status_code == 201
    
    # Second upload (duplicate)
    test_file.seek(0)
    response2 = client.post(
        "/api/v1/assets",
        files={"file": ("test.mp4", test_file, "video/mp4")}
    )
    assert response2.status_code == 409
```

## 15. Zusammenfassung

Diese vollständige Implementierungs-Spezifikation bietet:

### ✅ **Vollständige Docker-Umgebung**
- Multi-Service Architektur mit Docker Compose
- Entwicklungs- und Produktions-Konfigurationen
- Alle benötigten Datenbanken und Services

### ✅ **Detaillierte Service-Implementierungen**
- FastAPI für Python Services (2025 Best Practices)
- Go/Gin für High-Performance Query Service
- TypeScript MCP Server mit vollständiger Tool-Integration

### ✅ **Production-Ready Features**
- Comprehensive API Spezifikation (OpenAPI 3.0)
- Security mit JWT Authentication
- Monitoring mit Prometheus/Grafana
- CI/CD Pipeline mit GitHub Actions
- Backup & Recovery Strategien

### ✅ **Developer Experience**
- Makefile für einfache Commands
- Pre-commit Hooks für Code-Qualität
- Umfassende Test-Strategien
- Troubleshooting Guide

### **Nächste Schritte:**

1. **Setup starten:**
   ```bash
   git init dataflux
   cd dataflux
   # Kopiere alle Dateien aus der Spezifikation
   make setup
   make dev
   ```

2. **Services entwickeln:**
   - Beginne mit dem Ingestion Service
   - Implementiere Basic Video Analyzer
   - Teste End-to-End Workflow

3. **Iterativ erweitern:**
   - Füge weitere Analyzer hinzu
   - Optimiere Performance
   - Erweitere MCP Tools

Mit dieser Spezifikation hast du alles, was du brauchst, um DataFlux vollständig zu implementieren - von der lokalen Entwicklung bis zum Production Deployment!