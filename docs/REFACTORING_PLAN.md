# DataFlux - Refactoring-Plan für Modulare Code-Struktur

## 🎯 Zielsetzung

Transformation der monolithischen Codebase in eine modulare, wartbare und erweiterbare Architektur mit klarer Trennung der Verantwortlichkeiten.

## 📋 Refactoring-Strategie

### Phase 1: Service-Layer-Implementierung (Woche 1-2)
### Phase 2: Repository-Pattern (Woche 3-4)
### Phase 3: Configuration-Management (Woche 5-6)
### Phase 4: Testing-Infrastructure (Woche 7-8)
### Phase 5: Performance-Optimierung (Woche 9-10)

## 🏗️ Detaillierter Refactoring-Plan

### 1. Analysis Service Refactoring

#### Aktuelle Struktur
```
services/analysis-service/
├── src/
│   ├── main.py (443 Zeilen) ❌
│   ├── config.py
│   ├── claude_service.py
│   └── analyzers/
└── analyzers/ (29 Dateien)
```

#### Ziel-Struktur
```
services/analysis-service/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── middleware.py
│   │   └── dependencies.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analysis_service.py
│   │   ├── processing_service.py
│   │   ├── kafka_service.py
│   │   └── minio_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── asset_repository.py
│   │   ├── segment_repository.py
│   │   └── feature_repository.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── asset.py
│   │   ├── segment.py
│   │   ├── feature.py
│   │   └── analysis_result.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── image/
│   │   │   ├── __init__.py
│   │   │   ├── image_analyzer.py
│   │   │   ├── exif_extractor.py
│   │   │   ├── quality_analyzer.py
│   │   │   └── face_analyzer.py
│   │   ├── video/
│   │   │   ├── __init__.py
│   │   │   ├── video_analyzer.py
│   │   │   ├── scene_detector.py
│   │   │   ├── object_tracker.py
│   │   │   └── frame_extractor.py
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── audio_analyzer.py
│   │   │   ├── speech_extractor.py
│   │   │   └── music_analyzer.py
│   │   └── document/
│   │       ├── __init__.py
│   │       ├── document_analyzer.py
│   │       ├── docling_analyzer.py
│   │       └── pdf_analyzer.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   └── kafka.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   └── validators.py
│   ├── main.py (50 Zeilen) ✅
│   └── dependencies.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── e2e/
```

#### Refactoring-Schritte

##### Schritt 1: Service-Klassen erstellen
```python
# services/analysis-service/src/services/analysis_service.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from ..models.asset import Asset
from ..models.analysis_result import AnalysisResult
from ..repositories.asset_repository import AssetRepository
from ..analyzers.registry import AnalyzerRegistry

class AnalysisService(ABC):
    @abstractmethod
    async def analyze_asset(self, asset_id: str) -> AnalysisResult:
        pass

class AnalysisServiceImpl(AnalysisService):
    def __init__(
        self,
        asset_repository: AssetRepository,
        analyzer_registry: AnalyzerRegistry
    ):
        self.asset_repository = asset_repository
        self.analyzer_registry = analyzer_registry

    async def analyze_asset(self, asset_id: str) -> AnalysisResult:
        # Business Logic hier
        pass
```

##### Schritt 2: Repository-Pattern implementieren
```python
# services/analysis-service/src/repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
import asyncpg

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    @abstractmethod
    async def create(self, entity: T) -> T:
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        pass
```

##### Schritt 3: Analyzer-Registry implementieren
```python
# services/analysis-service/src/analyzers/registry.py
from typing import Dict, List, Optional
from .base import BaseAnalyzer
from .image.image_analyzer import ImageAnalyzer
from .video.video_analyzer import VideoAnalyzer
from .audio.audio_analyzer import AudioAnalyzer
from .document.document_analyzer import DocumentAnalyzer

class AnalyzerRegistry:
    def __init__(self):
        self._analyzers: Dict[str, BaseAnalyzer] = {}
        self._register_default_analyzers()

    def _register_default_analyzers(self):
        self.register('image', ImageAnalyzer())
        self.register('video', VideoAnalyzer())
        self.register('audio', AudioAnalyzer())
        self.register('document', DocumentAnalyzer())

    def register(self, media_type: str, analyzer: BaseAnalyzer):
        self._analyzers[media_type] = analyzer

    def get_analyzer(self, media_type: str) -> Optional[BaseAnalyzer]:
        return self._analyzers.get(media_type)

    def get_supported_types(self) -> List[str]:
        return list(self._analyzers.keys())
```

### 2. Ingestion Service Refactoring

#### Ziel-Struktur
```
services/ingestion-service/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── middleware.py
│   │   └── dependencies.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── upload_service.py
│   │   ├── processing_service.py
│   │   ├── thumbnail_service.py
│   │   └── duplicate_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── asset_repository.py
│   │   └── collection_repository.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── asset.py
│   │   ├── upload_request.py
│   │   └── thumbnail.py
│   ├── external/
│   │   ├── __init__.py
│   │   ├── minio_client.py
│   │   ├── kafka_producer.py
│   │   └── redis_client.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_utils.py
│   │   ├── hash_utils.py
│   │   └── mime_utils.py
│   ├── main.py (50 Zeilen) ✅
│   └── dependencies.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── e2e/
```

#### Refactoring-Schritte

##### Schritt 1: Upload-Service erstellen
```python
# services/ingestion-service/src/services/upload_service.py
from typing import Optional, Dict, Any
from ..models.asset import Asset
from ..models.upload_request import UploadRequest
from ..repositories.asset_repository import AssetRepository
from ..external.minio_client import MinIOClient
from ..external.kafka_producer import KafkaProducer
from ..utils.file_utils import FileUtils
from ..utils.hash_utils import HashUtils

class UploadService:
    def __init__(
        self,
        asset_repository: AssetRepository,
        minio_client: MinIOClient,
        kafka_producer: KafkaProducer,
        file_utils: FileUtils,
        hash_utils: HashUtils
    ):
        self.asset_repository = asset_repository
        self.minio_client = minio_client
        self.kafka_producer = kafka_producer
        self.file_utils = file_utils
        self.hash_utils = hash_utils

    async def upload_file(self, request: UploadRequest) -> Asset:
        # Upload Logic hier
        pass

    async def check_duplicate(self, file_hash: str) -> Optional[Asset]:
        # Duplicate Check Logic hier
        pass
```

##### Schritt 2: Thumbnail-Service erstellen
```python
# services/ingestion-service/src/services/thumbnail_service.py
from typing import List, Dict, Any
from ..models.thumbnail import Thumbnail
from ..external.minio_client import MinIOClient
from ..utils.file_utils import FileUtils

class ThumbnailService:
    def __init__(
        self,
        minio_client: MinIOClient,
        file_utils: FileUtils
    ):
        self.minio_client = minio_client
        self.file_utils = file_utils

    async def generate_thumbnails(
        self, 
        file_path: str, 
        asset_id: str
    ) -> List[Thumbnail]:
        # Thumbnail Generation Logic hier
        pass

    async def generate_single_thumbnail(
        self, 
        file_path: str, 
        size: str
    ) -> Thumbnail:
        # Single Thumbnail Logic hier
        pass
```

### 3. Query Service Refactoring

#### Ziel-Struktur
```
services/query-service/
├── cmd/
│   └── main.go (50 Zeilen) ✅
├── internal/
│   ├── api/
│   │   ├── handlers/
│   │   │   ├── search_handler.go
│   │   │   ├── similar_handler.go
│   │   │   └── health_handler.go
│   │   ├── middleware/
│   │   │   ├── cors.go
│   │   │   ├── logging.go
│   │   │   └── recovery.go
│   │   └── routes.go
│   ├── services/
│   │   ├── search_service.go
│   │   ├── nlp_service.go
│   │   ├── cache_service.go
│   │   └── ranking_service.go
│   ├── repositories/
│   │   ├── postgres_repository.go
│   │   ├── weaviate_repository.go
│   │   ├── neo4j_repository.go
│   │   └── redis_repository.go
│   ├── models/
│   │   ├── search.go
│   │   ├── result.go
│   │   └── nlp.go
│   ├── config/
│   │   └── config.go
│   └── utils/
│       ├── cache.go
│       └── validation.go
├── pkg/
│   ├── database/
│   ├── cache/
│   └── search/
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

#### Refactoring-Schritte

##### Schritt 1: Service-Interfaces definieren
```go
// services/query-service/internal/services/search_service.go
package services

import (
    "context"
    "dataflux/internal/models"
)

type SearchService interface {
    Search(ctx context.Context, req *models.SearchRequest) (*models.SearchResponse, error)
    FindSimilar(ctx context.Context, req *models.SimilarRequest) (*models.SearchResponse, error)
}

type searchServiceImpl struct {
    postgresRepo PostgresRepository
    weaviateRepo WeaviateRepository
    neo4jRepo    Neo4jRepository
    cacheService CacheService
    nlpService   NLPService
    rankingService RankingService
}

func NewSearchService(
    postgresRepo PostgresRepository,
    weaviateRepo WeaviateRepository,
    neo4jRepo Neo4jRepository,
    cacheService CacheService,
    nlpService NLPService,
    rankingService RankingService,
) SearchService {
    return &searchServiceImpl{
        postgresRepo: postgresRepo,
        weaviateRepo: weaviateRepo,
        neo4jRepo:    neo4jRepo,
        cacheService: cacheService,
        nlpService:   nlpService,
        rankingService: rankingService,
    }
}
```

##### Schritt 2: Repository-Interfaces definieren
```go
// services/query-service/internal/repositories/postgres_repository.go
package repositories

import (
    "context"
    "dataflux/internal/models"
)

type PostgresRepository interface {
    SearchAssets(ctx context.Context, keywords []string, filters map[string]interface{}, limit int) ([]*models.SearchResult, error)
    GetAssetByID(ctx context.Context, assetID string) (*models.Asset, error)
    GetSegmentsByAssetID(ctx context.Context, assetID string) ([]*models.Segment, error)
}

type postgresRepositoryImpl struct {
    db *pgxpool.Pool
}

func NewPostgresRepository(db *pgxpool.Pool) PostgresRepository {
    return &postgresRepositoryImpl{db: db}
}
```

### 4. Web UI Refactoring

#### Ziel-Struktur
```
services/web-ui/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Loading.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── layout/
│   │   │   ├── Layout.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   ├── assets/
│   │   │   ├── AssetGrid.tsx
│   │   │   ├── AssetCard.tsx
│   │   │   ├── AssetModal.tsx
│   │   │   └── AssetUpload.tsx
│   │   ├── search/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── SearchResults.tsx
│   │   │   └── SearchFilters.tsx
│   │   └── persons/
│   │       ├── PersonGrid.tsx
│   │       ├── PersonCard.tsx
│   │       └── PersonModal.tsx
│   ├── hooks/
│   │   ├── useAssets.ts
│   │   ├── useSearch.ts
│   │   ├── usePersons.ts
│   │   └── useUpload.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── assets.ts
│   │   ├── search.ts
│   │   └── persons.ts
│   ├── types/
│   │   ├── asset.ts
│   │   ├── search.ts
│   │   └── person.ts
│   ├── utils/
│   │   ├── api.ts
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── store/
│   │   ├── appStore.ts
│   │   ├── assetStore.ts
│   │   └── searchStore.ts
│   └── pages/
│       ├── index.tsx
│       ├── assets.tsx
│       ├── search.tsx
│       └── persons.tsx
└── tests/
    ├── components/
    ├── hooks/
    └── services/
```

#### Refactoring-Schritte

##### Schritt 1: Custom Hooks erstellen
```typescript
// services/web-ui/src/hooks/useAssets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { assetsService } from '../services/assets'
import { Asset, UploadRequest } from '../types/asset'

export const useAssets = (page = 1, limit = 20) => {
  return useQuery({
    queryKey: ['assets', page, limit],
    queryFn: () => assetsService.getAssets(page, limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useAsset = (assetId: string) => {
  return useQuery({
    queryKey: ['asset', assetId],
    queryFn: () => assetsService.getAsset(assetId),
    enabled: !!assetId,
  })
}

export const useUploadAsset = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (request: UploadRequest) => assetsService.uploadAsset(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
  })
}
```

##### Schritt 2: Service-Klassen erstellen
```typescript
// services/web-ui/src/services/assets.ts
import { api } from './api'
import { Asset, UploadRequest, AssetResponse } from '../types/asset'

export class AssetsService {
  async getAssets(page = 1, limit = 20): Promise<AssetResponse[]> {
    const response = await api.get(`/api/v1/assets?page=${page}&limit=${limit}`)
    return response.data
  }

  async getAsset(assetId: string): Promise<Asset> {
    const response = await api.get(`/api/v1/assets/${assetId}`)
    return response.data
  }

  async uploadAsset(request: UploadRequest): Promise<AssetResponse> {
    const formData = new FormData()
    formData.append('file', request.file)
    formData.append('context', request.context || '')
    formData.append('priority', request.priority.toString())
    
    const response = await api.post('/api/v1/assets', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async deleteAsset(assetId: string): Promise<void> {
    await api.delete(`/api/v1/assets/${assetId}`)
  }
}

export const assetsService = new AssetsService()
```

### 5. MCP Server Refactoring

#### Ziel-Struktur
```
services/mcp-server/
├── src/
│   ├── server/
│   │   ├── mcp_server.ts
│   │   ├── transport.ts
│   │   └── handlers.ts
│   ├── tools/
│   │   ├── search_tool.ts
│   │   ├── analyze_tool.ts
│   │   ├── similar_tool.ts
│   │   └── upload_tool.ts
│   ├── resources/
│   │   ├── statistics_resource.ts
│   │   └── health_resource.ts
│   ├── prompts/
│   │   ├── analyze_video_prompt.ts
│   │   └── search_insights_prompt.ts
│   ├── services/
│   │   ├── query_service.ts
│   │   ├── ingestion_service.ts
│   │   └── redis_service.ts
│   ├── types/
│   │   ├── tool.ts
│   │   ├── resource.ts
│   │   └── prompt.ts
│   ├── config/
│   │   └── config.ts
│   ├── utils/
│   │   ├── validation.ts
│   │   └── logging.ts
│   └── index.ts (50 Zeilen) ✅
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

#### Refactoring-Schritte

##### Schritt 1: Tool-Klassen erstellen
```typescript
// services/mcp-server/src/tools/search_tool.ts
import { Tool, ToolResult } from '../types/tool'
import { SearchRequestSchema } from '../utils/validation'
import { queryService } from '../services/query_service'
import { redisService } from '../services/redis_service'

export class SearchTool implements Tool {
  name = 'dataflux_search'
  description = 'Search DataFlux database for media content using natural language queries'
  inputSchema = SearchRequestSchema

  async execute(args: any): Promise<ToolResult> {
    try {
      const validatedArgs = SearchRequestSchema.parse(args)
      
      // Check cache first
      const cacheKey = `search:${JSON.stringify(validatedArgs)}`
      const cached = await redisService.get(cacheKey)
      
      if (cached) {
        return {
          content: [
            {
              type: 'text',
              text: `Found ${cached.total} cached results for query "${validatedArgs.query}":\n\n${JSON.stringify(cached.results, null, 2)}`,
            },
          ],
        }
      }

      // Call Query Service
      const response = await queryService.search(validatedArgs)
      
      // Cache results
      await redisService.setex(cacheKey, 300, JSON.stringify(response))
      
      return {
        content: [
          {
            type: 'text',
            text: `Found ${response.total} results for query "${validatedArgs.query}":\n\n${JSON.stringify(response.results, null, 2)}`,
          },
        ],
      }
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
        isError: true,
      }
    }
  }
}
```

## 🧪 Testing-Strategie

### Unit Tests
```python
# services/analysis-service/tests/unit/test_analysis_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.analysis_service import AnalysisServiceImpl
from src.repositories.asset_repository import AssetRepository
from src.analyzers.registry import AnalyzerRegistry

@pytest.fixture
def mock_asset_repository():
    return Mock(spec=AssetRepository)

@pytest.fixture
def mock_analyzer_registry():
    return Mock(spec=AnalyzerRegistry)

@pytest.fixture
def analysis_service(mock_asset_repository, mock_analyzer_registry):
    return AnalysisServiceImpl(mock_asset_repository, mock_analyzer_registry)

@pytest.mark.asyncio
async def test_analyze_asset_success(analysis_service, mock_asset_repository, mock_analyzer_registry):
    # Arrange
    asset_id = "test-asset-id"
    mock_asset = Mock()
    mock_analyzer = Mock()
    mock_result = Mock()
    
    mock_asset_repository.get_by_id.return_value = mock_asset
    mock_analyzer_registry.get_analyzer.return_value = mock_analyzer
    mock_analyzer.analyze.return_value = mock_result
    
    # Act
    result = await analysis_service.analyze_asset(asset_id)
    
    # Assert
    assert result == mock_result
    mock_asset_repository.get_by_id.assert_called_once_with(asset_id)
    mock_analyzer_registry.get_analyzer.assert_called_once()
    mock_analyzer.analyze.assert_called_once_with(mock_asset)
```

### Integration Tests
```python
# services/analysis-service/tests/integration/test_analysis_integration.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_analyze_asset_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/analyze", json={
            "asset_id": "test-asset-id",
            "analysis_type": "full"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "segments" in data["result"]
        assert "features" in data["result"]
```

## 📊 Performance-Metriken

### Code-Qualität-Metriken
- **Cyclomatic Complexity**: < 10 pro Funktion
- **Lines of Code**: < 200 pro Datei
- **Test Coverage**: > 80%
- **Code Duplication**: < 5%

### Architektur-Metriken
- **Service Separation**: Klare Trennung der Verantwortlichkeiten
- **Dependency Injection**: Loose Coupling zwischen Komponenten
- **Interface Segregation**: Kleine, fokussierte Interfaces
- **Single Responsibility**: Eine Verantwortlichkeit pro Klasse

### Wartbarkeits-Metriken
- **Time to Add Feature**: < 2 Stunden
- **Time to Fix Bug**: < 1 Stunde
- **Code Review Time**: < 30 Minuten
- **Onboarding Time**: < 1 Tag

## 🚀 Implementierungs-Timeline

### Woche 1-2: Analysis Service
- [ ] Service-Klassen erstellen
- [ ] Repository-Pattern implementieren
- [ ] Analyzer-Registry implementieren
- [ ] Unit Tests schreiben

### Woche 3-4: Ingestion Service
- [ ] Upload-Service erstellen
- [ ] Thumbnail-Service erstellen
- [ ] Repository-Pattern implementieren
- [ ] Integration Tests schreiben

### Woche 5-6: Query Service
- [ ] Go Package-Struktur implementieren
- [ ] Service-Interfaces definieren
- [ ] Repository-Interfaces definieren
- [ ] Unit Tests schreiben

### Woche 7-8: Web UI
- [ ] Custom Hooks erstellen
- [ ] Service-Klassen erstellen
- [ ] Komponenten aufteilen
- [ ] Component Tests schreiben

### Woche 9-10: MCP Server
- [ ] Tool-Klassen erstellen
- [ ] Service-Klassen erstellen
- [ ] Resource-Klassen erstellen
- [ ] Integration Tests schreiben

### Woche 11-12: Testing & Performance
- [ ] E2E Tests implementieren
- [ ] Performance-Optimierung
- [ ] Monitoring implementieren
- [ ] Dokumentation aktualisieren

## 🎯 Erfolgs-Kriterien

### Technische Kriterien
- [ ] Alle Services folgen dem Service-Layer-Pattern
- [ ] Repository-Pattern ist implementiert
- [ ] Dependency Injection ist konfiguriert
- [ ] Test Coverage > 80%
- [ ] Code Duplication < 5%

### Wartbarkeits-Kriterien
- [ ] Neue Features können in < 2 Stunden hinzugefügt werden
- [ ] Bugs können in < 1 Stunde gefixt werden
- [ ] Code Reviews dauern < 30 Minuten
- [ ] Neue Entwickler sind in < 1 Tag produktiv

### Performance-Kriterien
- [ ] API Response Times < 100ms (95th percentile)
- [ ] Search Queries < 200ms (95th percentile)
- [ ] Memory Usage < 512MB pro Service
- [ ] CPU Usage < 50% unter normaler Last

Dieser Refactoring-Plan stellt sicher, dass die DataFlux-Codebase modular, wartbar und erweiterbar wird, während die bestehende Funktionalität erhalten bleibt.