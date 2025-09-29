# DataFlux - Core System Architecture & Design Decisions

## 1. Fundamental Architecture Principles

### 1.1 System Philosophy
- **Core Principle**: Media-agnostic pipeline with pluggable analyzers
- **Hierarchy**: Parent-Child relationships (Film → Scenes → Frames → Objects)
- **Versioning**: Immutable versions, never overwrite
- **Multi-Tenancy**: Shared infrastructure with logical separation
- **Processing**: Hybrid batch/stream based on file size thresholds

### 1.2 Architecture Patterns
```
┌─────────────────────────────────────────────────────────────┐
│                   DataFlux Core Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Plugin Architecture Layer               │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │    │
│  │  │ Video  │ │ Image  │ │ Audio  │ │  Doc   │      │    │
│  │  │Analyzer│ │Analyzer│ │Analyzer│ │Analyzer│ ...  │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
│                            ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Core Processing Pipeline                  │    │
│  │   Ingestion → Segmentation → Analysis → Storage     │    │
│  └─────────────────────────────────────────────────────┘    │
│                            ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Intelligence Layer                      │    │
│  │   Embeddings → Relations → Similarity → Learning     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 2. Core Data Model

### 2.1 Universal Entity Model

```sql
-- Base entity for all content
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(50), -- 'asset', 'segment', 'collection'
    parent_id UUID REFERENCES entities(id),
    version INTEGER DEFAULT 1,
    version_of UUID REFERENCES entities(id), -- Points to original
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_latest BOOLEAN DEFAULT true,
    metadata JSONB
);

-- Assets (files)
CREATE TABLE assets (
    id UUID PRIMARY KEY REFERENCES entities(id),
    filename TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    storage_path TEXT,
    upload_context TEXT,
    processing_status VARCHAR(20),
    processing_priority INTEGER DEFAULT 5,
    UNIQUE(file_hash, version)
);

-- Universal segments
CREATE TABLE segments (
    id UUID PRIMARY KEY REFERENCES entities(id),
    asset_id UUID REFERENCES assets(id),
    segment_type VARCHAR(50), -- 'scene', 'paragraph', 'region'
    sequence_number INTEGER,
    start_marker JSONB, -- {time: 1.5} or {page: 1, line: 10}
    end_marker JSONB,
    confidence_score FLOAT
);

-- Features extracted from segments
CREATE TABLE features (
    id UUID PRIMARY KEY,
    segment_id UUID REFERENCES segments(id),
    feature_domain VARCHAR(50), -- 'visual', 'semantic', 'style', 'technical', 'audio'
    feature_type VARCHAR(100), -- 'object_detection', 'sentiment', etc.
    feature_data JSONB,
    confidence FLOAT,
    analyzer_version VARCHAR(50),
    created_at TIMESTAMP
);

-- Embeddings for vector search
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id),
    embedding_type VARCHAR(50), -- 'visual', 'text', 'audio', 'multimodal'
    model_name VARCHAR(100),
    vector_id VARCHAR(100), -- Reference to vector DB
    created_at TIMESTAMP
);

-- Relationships between entities
CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES entities(id),
    target_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(50), -- 'similar_to', 'derived_from', 'contains'
    strength FLOAT, -- 0.0 to 1.0
    metadata JSONB,
    created_at TIMESTAMP
);
```

### 2.2 Hierarchical Structure

```yaml
Asset (Movie.mp4)
├── Segment (Scene 1)
│   ├── Features (Objects: car, person)
│   ├── Features (Style: cinematic, dark)
│   └── Embeddings (CLIP, BLIP-2)
├── Segment (Scene 2)
│   ├── Features (Objects: building)
│   └── Features (Audio: dialogue)
└── Relationships
    ├── Similar_To → Other Asset
    └── Part_Of → Collection
```

## 3. Processing Pipeline Architecture

### 3.1 Processing Strategy

```python
class ProcessingStrategy:
    """Hybrid batch/stream processing based on file characteristics"""
    
    STREAMING_THRESHOLD = 100 * 1024 * 1024  # 100MB
    CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks
    
    @staticmethod
    def determine_strategy(file_size: int, mime_type: str) -> str:
        if file_size > ProcessingStrategy.STREAMING_THRESHOLD:
            return "STREAM"
        elif mime_type.startswith("video/"):
            return "CHUNKED"
        else:
            return "BATCH"
```

### 3.2 Queue Management

```yaml
Processing Queues (Kafka/RabbitMQ):
  high_priority:    # User-triggered, small files
    - priority: 1-3
    - workers: 5
  
  normal_priority:  # FIFO based on upload time
    - priority: 4-7
    - workers: 10
    
  low_priority:     # Bulk imports, re-processing
    - priority: 8-10
    - workers: 3
    
Queue Assignment:
  - file_size < 10MB: high_priority
  - file_size < 100MB: normal_priority
  - file_size >= 100MB: low_priority
  - bulk_import: always low_priority
```

### 3.3 Plugin Architecture

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAnalyzer(ABC):
    """Base class for all media analyzers"""
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported MIME types"""
        pass
    
    @abstractmethod
    def extract_segments(self, file_path: str, config: Dict) -> List[Segment]:
        """Extract segments from media file"""
        pass
    
    @abstractmethod
    def analyze_segment(self, segment: Segment, priorities: Dict) -> AnalysisResult:
        """Analyze a single segment based on priorities"""
        pass
    
    @abstractmethod
    def generate_embeddings(self, segment: Segment) -> List[Embedding]:
        """Generate embeddings for similarity search"""
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """Validate file before processing"""
        return True
    
    def get_metadata(self, file_path: str) -> Dict:
        """Extract file metadata"""
        return {}

class AnalysisResult:
    def __init__(self):
        self.features = {}  # domain -> feature_data
        self.confidence_scores = {}  # domain -> confidence
        self.processing_time = 0
        
class Segment:
    def __init__(self, segment_type: str, start: Any, end: Any):
        self.type = segment_type
        self.start_marker = start
        self.end_marker = end
        self.data = None  # Raw segment data
```

## 4. Storage Architecture

### 4.1 Storage Tiers

```yaml
Hot Storage (Redis/Memory):
  - Recently uploaded assets (< 24h)
  - Frequently accessed segments (> 10 hits/day)
  - Active search results
  - Processing queue metadata
  TTL: 24-48 hours

Warm Storage (PostgreSQL + Fast Object Storage):
  - Active assets (accessed within 30 days)
  - All metadata and relationships
  - Thumbnails and proxies
  - Recent embeddings
  TTL: 30-90 days

Cold Storage (S3 Glacier/Archive):
  - Inactive assets (> 90 days)
  - Original files only
  - Compressed analysis results
  - Old versions
  Retrieval: On-demand with 1-12h delay
```

### 4.2 Sharding Strategy

```yaml
Database Sharding:
  Strategy: Hybrid (Hash + Range)
  
  Primary Shard Key: entity_id (hash)
  Secondary Shard Key: created_at (range)
  
  Shard Distribution:
    - shard_1: hash(0-25%) + date(current_year)
    - shard_2: hash(26-50%) + date(current_year)
    - shard_3: hash(51-75%) + date(current_year)
    - shard_4: hash(76-100%) + date(current_year)
    - archive_shard: all + date(previous_years)
  
  Cross-Shard Queries:
    - Handled by query router
    - Parallel execution
    - Result aggregation
```

## 5. Event System

### 5.1 Core Events

```typescript
// Event definitions
interface DataFluxEvent {
  eventType: string;
  entityId: string;
  timestamp: Date;
  metadata: object;
}

// Critical events (always emitted)
const CRITICAL_EVENTS = [
  'asset.uploaded',
  'asset.processing_started',
  'asset.processing_completed',
  'asset.processing_failed',
  'segment.analyzed',
  'relationship.created',
  'version.created',
  'error.critical'
];

// Optional events (configurable)
const OPTIONAL_EVENTS = [
  'analysis.confidence_low',  // confidence < 0.5
  'similarity.match_found',    // similarity > 0.85
  'queue.threshold_exceeded',  // queue > 1000 items
  'storage.tier_moved',
  'feedback.received'
];
```

### 5.2 Event Processing

```yaml
Event Bus Architecture:
  
  Publisher (DataFlux Core):
    - Async event emission
    - Guaranteed delivery for critical events
    - Batch emission for performance
  
  Message Broker (Kafka/RabbitMQ):
    - Topic per event type
    - Retention: 7 days
    - Partitioning by entity_id
  
  Consumers:
    - Webhook Dispatcher
    - Analytics Pipeline
    - Audit Logger
    - Cache Invalidator
    - ML Training Pipeline
    
  Delivery Guarantees:
    - Critical events: At-least-once
    - Optional events: Best-effort
```

## 6. Permission System

### 6.1 Permission Model

```yaml
Permission Levels:
  
  System Level:
    - admin: Full system access
    - operator: Manage processing, view all
    - viewer: Read-only access to all
  
  Asset Level:
    - owner: Full control
    - editor: Modify, analyze, tag
    - viewer: View and search only
    
  Feature Level:
    - analyze: Trigger analysis
    - export: Download originals
    - delete: Remove assets
    - share: Create public links
    - api: API access
    
Permission Inheritance:
  Collection → Assets → Segments
  (Permissions flow downward)
```

### 6.2 Access Control Implementation

```sql
CREATE TABLE permissions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    entity_id UUID REFERENCES entities(id),
    permission_type VARCHAR(50),
    granted_at TIMESTAMP,
    granted_by UUID,
    expires_at TIMESTAMP,
    UNIQUE(user_id, entity_id, permission_type)
);

-- Materialized view for fast permission checks
CREATE MATERIALIZED VIEW user_permissions AS
SELECT 
    u.user_id,
    e.id as entity_id,
    array_agg(p.permission_type) as permissions
FROM users u
JOIN permissions p ON u.id = p.user_id
JOIN entities e ON p.entity_id = e.id
GROUP BY u.user_id, e.id;
```

## 7. Feedback & Learning System

### 7.1 Feedback Collection

```python
class FeedbackSystem:
    """Binary feedback for iterative improvement"""
    
    def collect_search_feedback(self, query_id: str, result_id: str, relevant: bool):
        """Track search result relevance"""
        feedback = {
            'type': 'search_relevance',
            'query_id': query_id,
            'result_id': result_id,
            'relevant': relevant,
            'timestamp': datetime.now()
        }
        self.store_feedback(feedback)
    
    def collect_analysis_feedback(self, segment_id: str, feature: str, correct: bool):
        """Track analysis accuracy"""
        feedback = {
            'type': 'analysis_accuracy',
            'segment_id': segment_id,
            'feature': feature,
            'correct': correct,
            'timestamp': datetime.now()
        }
        self.store_feedback(feedback)
```

### 7.2 Auto-Categorization

```python
class AutoCategorization:
    """Automatic collection and tag generation"""
    
    def auto_create_collections(self, assets: List[Asset]):
        """Group similar assets into collections"""
        # Cluster based on embeddings
        clusters = self.cluster_by_similarity(assets, threshold=0.75)
        
        for cluster in clusters:
            if len(cluster) >= 3:  # Minimum size for auto-collection
                collection = self.create_collection(
                    name=self.generate_collection_name(cluster),
                    assets=cluster,
                    auto_generated=True
                )
    
    def auto_tag(self, segment: Segment, features: Dict):
        """Generate tags from high-confidence features"""
        tags = []
        for domain, data in features.items():
            if data['confidence'] > 0.8:
                tags.extend(self.extract_tags(data))
        return tags
```

## 8. API & Integration Layer

### 8.1 Core API Structure

```yaml
/api/v1:
  # Asset Management
  /assets:
    POST: Upload asset
    GET: List assets (paginated)
  
  /assets/{id}:
    GET: Asset details + segments
    PUT: Update metadata
    DELETE: Soft delete
  
  /assets/{id}/analyze:
    POST: Trigger re-analysis
  
  /assets/{id}/versions:
    GET: List all versions
    POST: Create new version
  
  # Search & Discovery  
  /search:
    POST: Multi-modal search
    Body: {
      query: string | embedding,
      filters: {},
      limit: number,
      include_segments: boolean
    }
  
  /similar:
    POST: Find similar content
    Body: {
      entity_id: string,
      threshold: number,
      media_types: string[]
    }
  
  # Segments
  /segments/{id}:
    GET: Segment details
    POST: Update features
  
  # Relationships
  /relationships:
    POST: Create relationship
    GET: Query relationships
  
  # Feedback
  /feedback:
    POST: Submit feedback
  
  # System
  /status:
    GET: System health
  
  /stats:
    GET: Usage statistics
```

### 8.2 Webhook Configuration

```yaml
Webhook System:
  
  Configuration:
    - URL endpoint
    - Events to subscribe
    - Retry policy
    - Authentication method
  
  Delivery:
    - Max retries: 3
    - Backoff: Exponential
    - Timeout: 30s
    - Batch size: 10 events
  
  Payload Format:
    {
      "events": [...],
      "timestamp": "2024-01-01T00:00:00Z",
      "signature": "hmac-sha256-hash"
    }
```

## 9. Implementation Roadmap

### Phase 1: Core Foundation (Wochen 1-4)
- [x] Database schema implementation
- [ ] Basic ingestion pipeline
- [ ] Plugin architecture framework
- [ ] Simple video analyzer (scenes only)
- [ ] PostgreSQL + MinIO setup

### Phase 2: Processing Pipeline (Wochen 5-8)
- [ ] Queue management system
- [ ] Streaming processor for large files
- [ ] Version management
- [ ] Event bus implementation
- [ ] Basic permissions

### Phase 3: Intelligence Layer (Wochen 9-12)
- [ ] Embedding generation pipeline
- [ ] Vector database integration (Weaviate)
- [ ] Similarity calculation engine
- [ ] Relationship mapping (Neo4j)
- [ ] Auto-categorization

### Phase 4: API & Integration (Wochen 13-16)
- [ ] REST API implementation
- [ ] MCP server
- [ ] Webhook system
- [ ] Client SDKs (Python, JS)
- [ ] Admin dashboard

### Phase 5: Optimization (Wochen 17-20)
- [ ] Storage tiering automation
- [ ] Database sharding
- [ ] Cache optimization
- [ ] Performance tuning
- [ ] Monitoring & alerting

### Phase 6: Advanced Features (Wochen 21-24)
- [ ] Advanced analyzers (all media types)
- [ ] ML feedback loop
- [ ] Analytics dashboard
- [ ] Bulk import tools
- [ ] Export capabilities

## 10. Technology Decisions

### Confirmed Stack

```yaml
Core:
  Language: Python 3.11+ (AI/ML) + Go (API Server)
  Queue: Apache Kafka (better for streaming)
  Cache: Redis Cluster
  
Databases:
  Metadata: PostgreSQL 15+ with TimescaleDB
  Vectors: Weaviate (hybrid search)
  Relationships: Neo4j (graph traversal)
  Analytics: ClickHouse
  
Storage:
  Object Storage: MinIO (S3-compatible)
  Hot Tier: NVMe SSD
  Cold Tier: S3 Glacier
  
Infrastructure:
  Orchestration: Kubernetes
  Service Mesh: Istio
  Monitoring: Prometheus + Grafana
  Logging: ELK Stack
  
AI/ML:
  Framework: PyTorch 2.0
  Serving: TorchServe / Triton
  Embeddings: CLIP, BGE-M3
  Processing: Ray (distributed)
```

### Decision Rationale

**Kafka over RabbitMQ:**
- Better for streaming large files
- Superior replay capability
- Horizontal scaling

**Weaviate over Pinecone:**
- Self-hosted option
- Hybrid search (vector + keyword)
- Better data sovereignty

**PostgreSQL + Extensions:**
- Mature ecosystem
- TimescaleDB for time-series
- PostGIS for spatial data
- Strong consistency

## 11. Critical Success Factors

### Performance Targets
- Ingestion: < 2x realtime for video
- Search latency: < 200ms (p95)
- Processing queue: < 5 min wait (p95)
- API response: < 100ms (p95)

### Scalability Targets
- 1M+ assets
- 100M+ segments  
- 1000+ concurrent users
- 10TB+ storage

### Quality Targets
- Analysis accuracy: > 90%
- Search relevance: > 85%
- System uptime: 99.9%
- Data durability: 99.999%