# DataFlux - Cursor AI Implementation Guide & Prompts

## Phase 1: Project Setup (Tag 1)

### Task 1.1: Initialize Project Structure
**Cursor Prompt:**
```
Create a complete project structure for DataFlux, a microservices-based media analysis system. 
Structure needed:
- docker/ folder with docker-compose.yml for PostgreSQL, Redis, Kafka, MinIO, Weaviate, Neo4j, ClickHouse
- services/ folder with subfolders: ingestion-service, analysis-service, query-service, mcp-server
- Each service folder needs Dockerfile, requirements.txt/package.json, src/ folder
- scripts/ folder with init-db.sql, setup.sh
- Makefile with commands: setup, dev, stop, clean, logs, test, build
- .env.example with all necessary environment variables
- README.md with project overview
```

### Task 1.2: Docker Compose Setup
**Cursor Prompt:**
```
Create a production-ready docker-compose.yml with:
- PostgreSQL 16 with health checks, volume persistence, init script mounting
- Redis 7.2 with password auth, AOF persistence, maxmemory policy
- Apache Kafka 3.7 in KRaft mode (no Zookeeper), 3 partitions default
- MinIO latest with console, default buckets: dataflux-assets, dataflux-thumbnails, dataflux-proxies
- Weaviate 1.24 with text2vec-transformers module enabled
- Neo4j 5.15 community with APOC and GDS plugins
- ClickHouse 24.1 for analytics
- All services in network 'dataflux-network', with proper health checks
- Use YAML anchors for common variables (TZ, LOG_LEVEL, ENVIRONMENT)
- Add profiles for dev tools: pgadmin, kafka-ui, redis-commander
```

### Task 1.3: Database Schema
**Cursor Prompt:**
```
Create PostgreSQL schema in scripts/init-db.sql with:

Tables needed:
1. entities table: Base table with id, entity_type, parent_id, version, version_of, created_at, updated_at, is_latest, metadata JSONB
2. assets table: References entities, has filename, file_hash (unique with version), file_size, mime_type, storage_path, upload_context, processing_status, processing_priority
3. segments table: References entities and assets, has segment_type, sequence_number, start_marker JSONB, end_marker JSONB, confidence_score
4. features table: References segments, has feature_domain, feature_type, feature_data JSONB, confidence, analyzer_version
5. embeddings table: References entities, has embedding_type, model_name, vector_id
6. relationships table: Has source_id, target_id (both reference entities), relationship_type, strength (0-1), metadata JSONB

Add proper indexes for performance:
- Hash indexes on file_hash
- B-tree on created_at DESC
- GIN indexes on all JSONB columns
- Add pg_trgm extension for fuzzy text search
```

## Phase 2: Core Services (Tag 2-3)

### Task 2.1: Ingestion Service (FastAPI)
**Cursor Prompt:**
```
Create a FastAPI ingestion service in services/ingestion-service/src/main.py:

Requirements:
- FastAPI app with CORS enabled for all origins
- POST /api/v1/assets endpoint that:
  - Accepts file upload (multipart/form-data) 
  - Calculates SHA-256 hash for deduplication
  - Detects MIME type using python-magic
  - Stores file in MinIO with UUID-based path
  - Saves metadata to PostgreSQL
  - Publishes message to Kafka topic 'asset-processing'
  - Caches status in Redis with 1hr TTL
  - Returns 409 if duplicate hash exists
- GET /api/v1/assets/{id} to retrieve asset details
- GET /health endpoint
- Use asyncpg for PostgreSQL, aiokafka for Kafka, aioredis for Redis
- Dependency injection pattern for all connections
- Pydantic models for request/response validation
```

### Task 2.2: Query Service (Go)
**Cursor Prompt:**
```
Create a Go query service using Gin framework in services/query-service/cmd/main.go:

Requirements:
- Gin router with CORS middleware
- POST /api/v1/search endpoint that:
  - Accepts query, media_types[], filters{}, limit, include_segments
  - Checks Redis cache first (5min TTL)
  - Performs parallel searches: Weaviate (vector), PostgreSQL (text), Neo4j (graph)
  - Merges and ranks results by relevance score
  - Returns results with segments if requested
- POST /api/v1/similar for similarity search
- GET /api/v1/segments/{id} for segment details
- Connection pools for PostgreSQL (pgx), Redis (go-redis), Neo4j driver, Weaviate client
- Structured logging with request ID
- Graceful shutdown handling
```

### Task 2.3: MCP Server (TypeScript)
**Cursor Prompt:**
```
Create MCP server using @modelcontextprotocol/sdk in services/mcp-server/src/index.ts:

Requirements:
- Initialize McpServer with name "dataflux-mcp", version "1.0.0"
- Register 3 tools using zod schemas:
  1. dataflux_search: Natural language search with query, media_type, confidence_threshold, limit
  2. dataflux_analyze: Queue file for analysis with file_path, context, priority
  3. dataflux_similar: Find similar content with entity_id, threshold, limit
- Each tool calls appropriate service endpoints via axios
- Format responses for LLM consumption
- Register resource "statistics" that returns system stats from Redis
- Register prompt "analyze_video" with comprehensive analysis instructions
- Support both STDIO transport (for local dev) and SSE transport (for production)
- Express server on port 8004 with /sse endpoint
- Health check endpoint at /health
```

## Phase 3: Analysis Pipeline (Tag 3-4)

### Task 3.1: Kafka Consumer Setup
**Cursor Prompt:**
```
Create Kafka consumer in services/analysis-service/src/consumer.py:

Requirements:
- Consume from 'asset-processing' topic using aiokafka
- Consumer group 'analysis-consumers' with auto-commit
- Process messages based on mime_type routing:
  - video/* → VideoAnalyzer
  - image/* → ImageAnalyzer  
  - audio/* → AudioAnalyzer
  - application/pdf → DocumentAnalyzer
- Each analyzer should be a plugin inheriting from BaseAnalyzer
- Handle errors with exponential backoff retry (max 3 attempts)
- Update asset status in PostgreSQL: queued → processing → completed/failed
- Log processing metrics to ClickHouse
```

### Task 3.2: Video Analyzer Plugin
**Cursor Prompt:**
```
Create VideoAnalyzer plugin in services/analysis-service/src/analyzers/video.py:

Requirements:
- Inherit from BaseAnalyzer with methods: extract_segments, analyze_segment, generate_embeddings
- Scene detection using cv2 frame differencing (threshold: 30% change)
- Extract 1 frame per second for analysis
- For each scene, extract features in priority order:
  1. Visual: Object detection using YOLO v8, face detection, OCR
  2. Semantic: Action recognition, emotion detection using CLIP
  3. Style: Color palette, composition analysis
  4. Technical: Resolution, frame rate, codec info
  5. Audio: Speech-to-text using Whisper, music genre detection
- Generate embeddings using CLIP for visual, BGE-M3 for text
- Store features in PostgreSQL, embeddings in Weaviate
- Each feature gets confidence score (0-1)
- Create relationship edges in Neo4j for similar scenes (threshold > 0.75)
```

### Task 3.3: Weaviate Integration
**Cursor Prompt:**
```
Create Weaviate schema and client in services/shared/weaviate_client.py:

Requirements:
- Create schema classes: MediaAsset, MediaSegment with properties matching our features
- Batch import with error handling and retry logic
- Hybrid search method combining vector and keyword search
- Methods needed:
  - create_schema(): Define classes with text2vec-transformers
  - store_embeddings(): Batch import with 100 items per batch
  - search_similar(): nearVector search with distance threshold
  - hybrid_search(): Combine BM25 and vector search
- Connection pooling with health check
- Automatic reconnection on failure
```

## Phase 4: Frontend & API Gateway (Tag 4-5)

### Task 4.1: API Gateway Configuration
**Cursor Prompt:**
```
Create Nginx configuration in services/api-gateway/nginx.conf:

Requirements:
- Upstream blocks for each service with health checks
- Rate limiting: 100 requests per minute per IP
- Request body size limit: 500MB for file uploads
- Routing rules:
  - /api/v1/assets/* → ingestion-service:8001
  - /api/v1/search/* → query-service:8002
  - /api/v1/analyze/* → analysis-service:8003
  - /api/mcp/* → mcp-server:8004
- CORS headers configuration
- Gzip compression for responses
- Request/response logging in JSON format
- SSL configuration with Let's Encrypt
- Security headers (HSTS, X-Frame-Options, CSP)
```

### Task 4.2: Web Dashboard
**Cursor Prompt:**
```
Create Next.js dashboard in services/web-ui:

Pages needed:
1. / - Dashboard with stats (total assets, processing queue, storage usage)
2. /upload - Drag & drop file upload with progress bar
3. /search - Search interface with filters and result grid
4. /asset/[id] - Asset detail page with segments timeline
5. /collections - Collection management

Components needed:
- FileUploader with chunked upload support
- SearchBar with autocomplete
- AssetGrid with lazy loading
- SegmentTimeline with preview thumbnails
- StatsCards for metrics display

Use:
- Tailwind CSS for styling
- React Query for data fetching
- Zustand for state management
- Recharts for analytics visualization
```

## Phase 5: Production Readiness (Tag 5-6)

### Task 5.1: Monitoring Setup
**Cursor Prompt:**
```
Add Prometheus metrics to all services:

For each service add:
- Request count by endpoint and status code
- Request duration histogram
- Active connections gauge
- Custom business metrics:
  - Assets processed per minute
  - Average confidence score
  - Queue depth by priority
  - Storage usage by type

Create Grafana dashboards:
1. System Overview: CPU, memory, disk, network for all containers
2. Application Metrics: Request rate, error rate, latency percentiles
3. Business Metrics: Assets processed, search queries, popular content
4. Alerts Dashboard: Failed services, high error rates, queue backlog

Setup alerting rules for:
- Service down > 1 minute
- Error rate > 5%
- Queue depth > 1000
- Disk usage > 80%
```

### Task 5.2: Testing Suite
**Cursor Prompt:**
```
Create comprehensive test suite:

Unit tests for each service:
- Test deduplication logic
- Test file type detection
- Test search ranking algorithm
- Mock all external dependencies

Integration tests:
- Upload file → Process → Search flow
- Duplicate detection across services
- Database transaction rollback
- Cache invalidation

E2E tests using Playwright:
- Upload video file
- Wait for processing
- Search for content
- Verify segments appear

Performance tests using k6:
- Upload 100 files simultaneously
- Search with 1000 concurrent users
- Measure response times and throughput
```

### Task 5.3: CI/CD Pipeline
**Cursor Prompt:**
```
Create GitHub Actions workflow in .github/workflows/main.yml:

Jobs needed:
1. Test job: Run unit tests for all services in parallel
2. Build job: Build Docker images with layer caching
3. Security scan: Trivy for vulnerabilities, SAST for code
4. Deploy job: Deploy to Kubernetes using Helm charts

For each service create:
- Dockerfile with multi-stage build
- .dockerignore file
- Helm chart with configurable replicas, resources, ingress

Setup:
- Semantic versioning with tags
- Automatic changelog generation
- Docker image push to GitHub Container Registry
- Environment-specific configs (dev, staging, prod)
```

## Phase 6: Optimization (Tag 6-7)

### Task 6.1: Performance Optimization
**Cursor Prompt:**
```
Optimize system performance:

Database optimizations:
- Add materialized views for common queries
- Implement database connection pooling
- Add Redis caching for hot data
- Optimize PostgreSQL: increase shared_buffers, effective_cache_size

Code optimizations:
- Implement request batching for Weaviate
- Add circuit breakers for external services
- Use streaming for large file uploads
- Implement progressive JPEG/WebP for thumbnails

Infrastructure optimizations:
- Enable HTTP/2 in Nginx
- Add CDN for static assets
- Implement horizontal pod autoscaling
- Use node affinity for GPU workloads
```

### Task 6.2: Advanced Features
**Cursor Prompt:**
```
Add advanced features:

1. Smart Deduplication:
   - Perceptual hashing for similar images
   - Audio fingerprinting for duplicate audio
   - Fuzzy matching for near-duplicates

2. Auto-tagging:
   - Cluster similar content automatically
   - Generate collections based on themes
   - Suggest tags based on content analysis

3. Feedback Loop:
   - Store user corrections
   - Retrain models monthly
   - A/B test new models
   - Track precision/recall metrics

4. Export/Import:
   - Export collections as JSON/CSV
   - Bulk import with validation
   - API client SDKs (Python, JS, Go)
```

## Cursor Workflow Tips

### How to use this guide with Cursor:

1. **Start with Phase 1**: Copy each prompt one by one
2. **Let Cursor generate**: Review and accept the code
3. **Test incrementally**: Run `docker-compose up` after each service
4. **Fix issues**: Ask Cursor to debug specific errors
5. **Iterate quickly**: Don't perfect everything, get it working first

### Cursor Commands to Use:

- `Cmd+K`: For quick edits
- `Cmd+L`: For chat about specific code
- `Cmd+Shift+L`: Add whole file to context
- `@workspace`: Reference entire project
- `@web`: Search for latest packages/solutions

### Example Cursor Debug Prompts:

```
"Fix this PostgreSQL connection error: [paste error]"
"Add retry logic to this Kafka consumer"
"Optimize this Weaviate query for better performance"
"Add proper error handling to this upload endpoint"
```

## Realistic Timeline

With Cursor AI assistance, working full-time:
- **Day 1**: Complete Phase 1 (Setup)
- **Day 2-3**: Complete Phase 2 (Core Services)
- **Day 3-4**: Complete Phase 3 (Analysis Pipeline)
- **Day 4-5**: Complete Phase 4 (Frontend)
- **Day 5-6**: Complete Phase 5 (Production)
- **Day 6-7**: Complete Phase 6 (Optimization)

Total: **1 week for MVP**, 2 weeks for production-ready system