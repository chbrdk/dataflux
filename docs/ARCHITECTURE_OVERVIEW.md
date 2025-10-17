# DataFlux - Architektur-Übersicht

## 🏗️ System-Architektur

DataFlux ist eine **Universal AI-native Database** für Medieninhalte mit einer modularen Microservices-Architektur.

### Kern-Prinzipien

1. **Media-Agnostic Pipeline**: Unterstützt Video, Audio, Bilder und Dokumente
2. **Plugin-Architektur**: Erweiterbare Analyzer für neue Medienformate
3. **Multi-Modal Search**: Cross-Modal Queries über verschiedene Medientypen
4. **Hybrid Processing**: Batch & Stream Verarbeitung je nach Dateigröße
5. **Skalierbare Architektur**: Horizontale Skalierung aller Komponenten

## 🎯 Services-Übersicht

### 1. Ingestion Service (Port 8002)
- **Technologie**: FastAPI, Python
- **Zweck**: File Upload, Deduplication, Processing Queue Management
- **Features**:
  - Streaming File Upload mit automatischer Verarbeitung
  - Hash-basierte Duplikaterkennung
  - MinIO Storage Integration
  - Kafka Message Publishing
  - Multi-Thumbnail-Generierung (Small/Medium/Large)

### 2. Analysis Service (Port 2014)
- **Technologie**: FastAPI, Python, OpenCV, YOLO, DeepFace, FaceNet, CLIP, Claude Vision
- **Zweck**: KI-gestützte Analyse von Medieninhalten
- **Features**:
  - Plugin-basierte Analyzer (Image, Video, Audio, Document, Docling)
  - AI/ML Model Integration
  - Feature Extraction und Segmentierung
  - Embedding Generation für Vector Search
  - Docling Document Analysis (PDF, Office, HTML)

### 3. Query Service (Port 8003)
- **Technologie**: Go, Gin, PostgreSQL, Redis, Weaviate, Neo4j
- **Zweck**: Multi-Modal Search Engine
- **Features**:
  - Natural Language Query Processing
  - Vector Search (Weaviate)
  - Graph Queries (Neo4j)
  - Full-text Search (PostgreSQL)
  - Redis Caching

### 4. Auth Service (Port 8006)
- **Technologie**: FastAPI, Python, JWT
- **Zweck**: Authentication und Authorization
- **Features**:
  - JWT Token Management
  - Role-Based Access Control (RBAC)
  - User Management
  - Session Management

### 5. MCP Server (Ports 2015/2016)
- **Technologie**: TypeScript, Node.js
- **Zweck**: LLM Integration und Tool Registration
- **Features**:
  - Tool Registration für LLMs
  - Resource Management
  - Prompt Templates
  - Service Integration

### 6. Web UI (Port 3000)
- **Technologie**: Next.js, React, TypeScript, Tailwind CSS
- **Zweck**: Benutzeroberfläche
- **Features**:
  - Asset Management
  - Search Interface
  - Analytics Dashboard
  - Personen-Management
  - Glassmorphismus-Modal

### 7. API Gateway (Ports 2013/2014)
- **Technologie**: Nginx
- **Zweck**: Request Routing und Load Balancing
- **Features**:
  - Request Routing
  - Rate Limiting
  - CORS Handling
  - SSL/TLS Termination

## 🗄️ Datenbank-Architektur

### PostgreSQL (Port 2001)
- **Zweck**: Hauptdatenbank für Metadaten
- **Tabellen**:
  - `entities`: Zentrale Entitäts-Tabelle
  - `assets`: Asset-Metadaten
  - `segments`: Medien-Segmente
  - `features`: Extrahierte Features
  - `embeddings`: Vector Embeddings
  - `relationships`: Entitäts-Beziehungen

### Redis (Port 2002)
- **Zweck**: Caching und Session Management
- **Features**:
  - Search Result Caching
  - Session Storage
  - Rate Limiting
  - Real-time Updates

### Weaviate (Port 2005)
- **Zweck**: Vector Database für Semantic Search
- **Features**:
  - Vector Similarity Search
  - Multi-modal Embeddings
  - GraphQL API
  - Real-time Indexing

### Neo4j (Port 2007)
- **Zweck**: Graph Database für Beziehungen
- **Features**:
  - Graph Traversal
  - Relationship Analysis
  - Cypher Queries
  - APOC Procedures

### ClickHouse (Port 2011)
- **Zweck**: Analytics und Time-Series Data
- **Features**:
  - High-Performance Analytics
  - Time-Series Queries
  - Aggregation Functions
  - Real-time Dashboards

### MinIO (Port 2003)
- **Zweck**: Object Storage für Medien-Dateien
- **Features**:
  - S3-compatible API
  - Multi-Bucket Organization
  - Lifecycle Management
  - Access Control

## 🔄 Datenfluss

### 1. Asset Upload Flow
```
Web UI → API Gateway → Ingestion Service → MinIO + PostgreSQL → Kafka
```

### 2. Analysis Processing Flow
```
Kafka → Analysis Service → AI Models → PostgreSQL + Weaviate + Neo4j
```

### 3. Search Flow
```
Web UI → API Gateway → Query Service → Redis Cache → PostgreSQL/Weaviate/Neo4j
```

## 📊 Monitoring & Observability

### Prometheus (Port 2020)
- **Zweck**: Metrics Collection
- **Features**:
  - Service Health Metrics
  - Performance Metrics
  - Business Metrics
  - Custom Metrics

### Grafana (Port 2021)
- **Zweck**: Metrics Visualization
- **Features**:
  - System Overview Dashboards
  - Service Health Dashboards
  - Business Intelligence
  - Alerting

## 🚀 Deployment

### Docker Compose (Development)
- **Zweck**: Lokale Entwicklung
- **Features**:
  - Service Orchestration
  - Volume Management
  - Network Configuration
  - Environment Variables

### Kubernetes (Production)
- **Zweck**: Production Deployment
- **Features**:
  - Auto-scaling
  - Load Balancing
  - Service Discovery
  - Health Checks

## 🔧 Konfiguration

### Port-Mapping
- **API Gateway**: 2013 (HTTP), 2014 (HTTPS)
- **Ingestion Service**: 8002
- **Analysis Service**: 2014
- **Query Service**: 8003
- **Auth Service**: 8006
- **MCP Server**: 2015, 2016
- **Web UI**: 3000
- **PostgreSQL**: 2001
- **Redis**: 2002
- **MinIO**: 2003, 2004
- **Weaviate**: 2005, 2006
- **Neo4j**: 2007, 2008
- **Kafka**: 2009, 2010
- **ClickHouse**: 2011, 2012
- **Prometheus**: 2020
- **Grafana**: 2021

### Umgebungsvariablen
- `DATABASE_URL`: PostgreSQL Connection String
- `REDIS_URL`: Redis Connection String
- `KAFKA_BROKERS`: Kafka Broker URLs
- `MINIO_ENDPOINT`: MinIO Endpoint
- `WEAVIATE_URL`: Weaviate URL
- `NEO4J_URI`: Neo4j Connection String
- `CLAUDE_API_KEY`: Anthropic API Key
- `OPENAI_API_KEY`: OpenAI API Key

## 📈 Performance-Ziele

### Response Times
- **Search Queries**: < 200ms (95th percentile)
- **Asset Upload**: < 5s für Dateien < 100MB
- **Analysis Processing**: < 30s für 1-Minuten-Video
- **API Responses**: < 100ms (95th percentile)

### Throughput
- **Concurrent Users**: 10,000+
- **Assets per Hour**: 100,000+
- **Search Queries per Second**: 1,000+
- **Data Processing**: 1TB/hour

## 🔒 Sicherheit

### Authentication
- **JWT Tokens**: Stateless Authentication
- **RBAC**: Role-Based Access Control
- **Session Management**: Redis-based Sessions

### Network Security
- **mTLS**: Mutual TLS zwischen Services
- **API Keys**: Service-spezifische Authentifizierung
- **Rate Limiting**: Per-User Rate Limiting

### Data Encryption
- **At Rest**: AES-256 Verschlüsselung
- **In Transit**: TLS 1.3 für alle Kommunikation
- **Key Management**: HashiCorp Vault Integration

## 🎯 Zukünftige Erweiterungen

### Geplante Features
- **Custom Models**: User-spezifische Modell-Training
- **Real-time Learning**: Kontinuierliche Modell-Verbesserung
- **Multi-modal Fusion**: Cross-Modal Understanding
- **Edge Computing**: CDN Integration für globale Performance
- **GPU Acceleration**: CUDA Support für ML Workloads

### Enterprise Features
- **Multi-tenancy**: Isolierte Kunden-Umgebungen
- **Advanced Analytics**: Business Intelligence Dashboards
- **Document Workflow**: Automatisierte Dokumentenverarbeitung
- **API Rate Limiting**: Erweiterte Rate Limiting Features