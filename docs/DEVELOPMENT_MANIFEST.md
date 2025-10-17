# DataFlux - Entwicklungs-Manifest

## 🎯 Prinzipien für zukünftige Implementierungen

### 1. Clean Architecture Prinzipien

#### Domain-Driven Design (DDD)
- **Entities**: Kern-Business-Objekte (Asset, Segment, Feature)
- **Value Objects**: Unveränderliche Objekte (Thumbnail, Embedding)
- **Aggregates**: Konsistente Einheiten (Asset mit Segments)
- **Repositories**: Datenzugriff-Abstraktionen
- **Services**: Business Logic ohne State

#### Separation of Concerns
```
├── Presentation Layer (API/UI)
├── Application Layer (Use Cases)
├── Domain Layer (Business Logic)
└── Infrastructure Layer (External Services)
```

### 2. Code-Organisation

#### Service-Struktur
```
services/{service-name}/
├── src/
│   ├── api/              # HTTP Layer (Routes, Middleware)
│   ├── services/         # Business Logic
│   ├── repositories/     # Data Access
│   ├── models/           # Data Models
│   ├── external/         # External Service Clients
│   ├── config/           # Configuration
│   ├── utils/            # Utilities
│   └── main.py/go/ts     # Entry Point
├── tests/
│   ├── unit/             # Unit Tests
│   ├── integration/      # Integration Tests
│   └── e2e/              # End-to-End Tests
└── docs/                 # Service-spezifische Dokumentation
```

#### Datei-Größen-Limits
- **Python**: Max 200 Zeilen pro Datei
- **Go**: Max 300 Zeilen pro Datei
- **TypeScript**: Max 250 Zeilen pro Datei
- **React Components**: Max 150 Zeilen pro Komponente

### 3. Naming Conventions

#### Python
```python
# Klassen: PascalCase
class AssetRepository:
    pass

# Funktionen: snake_case
def get_asset_by_id(asset_id: str) -> Asset:
    pass

# Konstanten: UPPER_SNAKE_CASE
DATABASE_URL = "postgresql://..."

# Private Methoden: _snake_case
def _validate_asset(asset: Asset) -> bool:
    pass
```

#### Go
```go
// Interfaces: -er Suffix
type AssetRepository interface {
    GetByID(ctx context.Context, id string) (*Asset, error)
}

// Structs: PascalCase
type AssetRepositoryImpl struct {
    db *pgxpool.Pool
}

// Funktionen: PascalCase (exported), camelCase (private)
func NewAssetRepository(db *pgxpool.Pool) AssetRepository {
    return &AssetRepositoryImpl{db: db}
}

func (r *AssetRepositoryImpl) getByID(ctx context.Context, id string) (*Asset, error) {
    // Implementation
}
```

#### TypeScript
```typescript
// Interfaces: PascalCase
interface AssetRepository {
  getById(id: string): Promise<Asset>
}

// Klassen: PascalCase
class AssetRepositoryImpl implements AssetRepository {
  // Implementation
}

// Funktionen: camelCase
async function getAssetById(id: string): Promise<Asset> {
  // Implementation
}

// Konstanten: UPPER_SNAKE_CASE
const API_BASE_URL = 'http://localhost:8000'
```

### 4. Dependency Injection

#### Python (FastAPI)
```python
# dependencies.py
from functools import lru_cache
from .repositories.asset_repository import AssetRepository
from .services.asset_service import AssetService

@lru_cache()
def get_asset_repository() -> AssetRepository:
    return AssetRepositoryImpl()

@lru_cache()
def get_asset_service(
    asset_repo: AssetRepository = Depends(get_asset_repository)
) -> AssetService:
    return AssetService(asset_repo)

# routes.py
@app.get("/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service)
):
    return await asset_service.get_asset(asset_id)
```

#### Go (Gin)
```go
// dependencies.go
type Dependencies struct {
    AssetRepository repositories.AssetRepository
    AssetService    services.AssetService
}

func NewDependencies() *Dependencies {
    db := initDatabase()
    assetRepo := repositories.NewAssetRepository(db)
    assetService := services.NewAssetService(assetRepo)
    
    return &Dependencies{
        AssetRepository: assetRepo,
        AssetService:    assetService,
    }
}

// handlers.go
func (h *Handler) GetAsset(c *gin.Context) {
    assetID := c.Param("id")
    asset, err := h.deps.AssetService.GetAsset(c.Request.Context(), assetID)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, asset)
}
```

#### TypeScript (NestJS)
```typescript
// asset.service.ts
@Injectable()
export class AssetService {
  constructor(
    private readonly assetRepository: AssetRepository,
  ) {}

  async getAsset(id: string): Promise<Asset> {
    return this.assetRepository.findById(id)
  }
}

// asset.controller.ts
@Controller('assets')
export class AssetController {
  constructor(private readonly assetService: AssetService) {}

  @Get(':id')
  async getAsset(@Param('id') id: string): Promise<Asset> {
    return this.assetService.getAsset(id)
  }
}
```

### 5. Error Handling

#### Python
```python
# exceptions.py
class DataFluxException(Exception):
    """Base exception for DataFlux services"""
    pass

class AssetNotFoundError(DataFluxException):
    """Asset not found exception"""
    pass

class ValidationError(DataFluxException):
    """Validation error exception"""
    pass

# service.py
async def get_asset(self, asset_id: str) -> Asset:
    try:
        asset = await self.asset_repository.get_by_id(asset_id)
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        return asset
    except DatabaseError as e:
        logger.error(f"Database error getting asset {asset_id}: {e}")
        raise DataFluxException("Internal server error") from e
```

#### Go
```go
// errors.go
var (
    ErrAssetNotFound = errors.New("asset not found")
    ErrValidation    = errors.New("validation error")
    ErrInternal      = errors.New("internal server error")
)

// service.go
func (s *AssetService) GetAsset(ctx context.Context, assetID string) (*Asset, error) {
    asset, err := s.assetRepository.GetByID(ctx, assetID)
    if err != nil {
        if errors.Is(err, pgx.ErrNoRows) {
            return nil, ErrAssetNotFound
        }
        log.Printf("Database error getting asset %s: %v", assetID, err)
        return nil, ErrInternal
    }
    return asset, nil
}
```

#### TypeScript
```typescript
// exceptions.ts
export class DataFluxException extends Error {
  constructor(message: string, public statusCode: number = 500) {
    super(message)
    this.name = 'DataFluxException'
  }
}

export class AssetNotFoundError extends DataFluxException {
  constructor(assetId: string) {
    super(`Asset ${assetId} not found`, 404)
    this.name = 'AssetNotFoundError'
  }
}

// service.ts
async getAsset(id: string): Promise<Asset> {
  try {
    const asset = await this.assetRepository.findById(id)
    if (!asset) {
      throw new AssetNotFoundError(id)
    }
    return asset
  } catch (error) {
    if (error instanceof DataFluxException) {
      throw error
    }
    logger.error(`Database error getting asset ${id}:`, error)
    throw new DataFluxException('Internal server error')
  }
}
```

### 6. Logging Standards

#### Python
```python
# logging.py
import structlog
import logging

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# service.py
logger = structlog.get_logger(__name__)

async def process_asset(self, asset_id: str):
    logger.info("Processing asset", asset_id=asset_id)
    try:
        # Processing logic
        logger.info("Asset processed successfully", asset_id=asset_id)
    except Exception as e:
        logger.error("Failed to process asset", asset_id=asset_id, error=str(e))
        raise
```

#### Go
```go
// logging.go
import (
    "log/slog"
    "os"
)

func setupLogging() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)
}

// service.go
func (s *AssetService) ProcessAsset(ctx context.Context, assetID string) error {
    slog.Info("Processing asset", "asset_id", assetID)
    
    if err := s.processAsset(ctx, assetID); err != nil {
        slog.Error("Failed to process asset", "asset_id", assetID, "error", err)
        return err
    }
    
    slog.Info("Asset processed successfully", "asset_id", assetID)
    return nil
}
```

#### TypeScript
```typescript
// logging.ts
import winston from 'winston'

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
})

// service.ts
async processAsset(assetId: string): Promise<void> {
  logger.info('Processing asset', { assetId })
  
  try {
    await this.processAssetInternal(assetId)
    logger.info('Asset processed successfully', { assetId })
  } catch (error) {
    logger.error('Failed to process asset', { assetId, error })
    throw error
  }
}
```

### 7. Testing Standards

#### Unit Tests
```python
# test_asset_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.asset_service import AssetService
from src.repositories.asset_repository import AssetRepository

@pytest.fixture
def mock_asset_repository():
    return Mock(spec=AssetRepository)

@pytest.fixture
def asset_service(mock_asset_repository):
    return AssetService(mock_asset_repository)

@pytest.mark.asyncio
async def test_get_asset_success(asset_service, mock_asset_repository):
    # Arrange
    asset_id = "test-asset-id"
    expected_asset = Mock()
    mock_asset_repository.get_by_id.return_value = expected_asset
    
    # Act
    result = await asset_service.get_asset(asset_id)
    
    # Assert
    assert result == expected_asset
    mock_asset_repository.get_by_id.assert_called_once_with(asset_id)
```

#### Integration Tests
```python
# test_asset_integration.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_get_asset_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/assets/test-asset-id")
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "filename" in data
```

### 8. Configuration Management

#### Python
```python
# config/settings.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://localhost:5432/dataflux"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Kafka
    kafka_brokers: str = "localhost:9092"
    
    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    
    # API Keys
    claude_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

#### Go
```go
// config/config.go
type Config struct {
    Database struct {
        URL string `env:"DATABASE_URL" envDefault:"postgresql://localhost:5432/dataflux"`
    }
    Redis struct {
        URL string `env:"REDIS_URL" envDefault:"redis://localhost:6379"`
    }
    Kafka struct {
        Brokers string `env:"KAFKA_BROKERS" envDefault:"localhost:9092"`
    }
    MinIO struct {
        Endpoint    string `env:"MINIO_ENDPOINT" envDefault:"localhost:9000"`
        AccessKey   string `env:"MINIO_ACCESS_KEY" envDefault:"minioadmin"`
        SecretKey   string `env:"MINIO_SECRET_KEY" envDefault:"minioadmin123"`
    }
    APIKeys struct {
        ClaudeAPIKey string `env:"CLAUDE_API_KEY"`
        OpenAIAPIKey string `env:"OPENAI_API_KEY"`
    }
}

func LoadConfig() (*Config, error) {
    cfg := &Config{}
    if err := env.Parse(cfg); err != nil {
        return nil, err
    }
    return cfg, nil
}
```

#### TypeScript
```typescript
// config/config.ts
export interface Config {
  database: {
    url: string
  }
  redis: {
    url: string
  }
  kafka: {
    brokers: string
  }
  minio: {
    endpoint: string
    accessKey: string
    secretKey: string
  }
  apiKeys: {
    claudeApiKey?: string
    openaiApiKey?: string
  }
}

export const config: Config = {
  database: {
    url: process.env.DATABASE_URL || 'postgresql://localhost:5432/dataflux'
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379'
  },
  kafka: {
    brokers: process.env.KAFKA_BROKERS || 'localhost:9092'
  },
  minio: {
    endpoint: process.env.MINIO_ENDPOINT || 'localhost:9000',
    accessKey: process.env.MINIO_ACCESS_KEY || 'minioadmin',
    secretKey: process.env.MINIO_SECRET_KEY || 'minioadmin123'
  },
  apiKeys: {
    claudeApiKey: process.env.CLAUDE_API_KEY,
    openaiApiKey: process.env.OPENAI_API_KEY
  }
}
```

### 9. API Design Standards

#### RESTful APIs
```python
# routes.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from .models.asset import Asset, AssetCreate, AssetUpdate
from .services.asset_service import AssetService

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

@router.get("/", response_model=List[Asset])
async def list_assets(
    page: int = 1,
    limit: int = 20,
    asset_service: AssetService = Depends(get_asset_service)
):
    """List assets with pagination"""
    return await asset_service.list_assets(page, limit)

@router.get("/{asset_id}", response_model=Asset)
async def get_asset(
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service)
):
    """Get asset by ID"""
    asset = await asset_service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.post("/", response_model=Asset, status_code=201)
async def create_asset(
    asset_data: AssetCreate,
    asset_service: AssetService = Depends(get_asset_service)
):
    """Create new asset"""
    return await asset_service.create_asset(asset_data)

@router.put("/{asset_id}", response_model=Asset)
async def update_asset(
    asset_id: str,
    asset_data: AssetUpdate,
    asset_service: AssetService = Depends(get_asset_service)
):
    """Update asset"""
    asset = await asset_service.update_asset(asset_id, asset_data)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service)
):
    """Delete asset"""
    success = await asset_service.delete_asset(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
```

### 10. Performance Standards

#### Caching Strategy
```python
# services/cache_service.py
from typing import Any, Optional
import redis
import json
from functools import wraps

class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL"""
        await self.redis.setex(key, ttl, json.dumps(value))
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        await self.redis.delete(key)

def cache_result(ttl: int = 300):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached = await cache_service.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

#### Database Optimization
```python
# repositories/asset_repository.py
from typing import List, Optional
import asyncpg
from sqlalchemy import select, and_
from .base_repository import BaseRepository
from ..models.asset import Asset

class AssetRepository(BaseRepository[Asset]):
    async def get_by_id(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID with optimized query"""
        query = select(Asset).where(Asset.id == asset_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_assets(
        self, 
        page: int = 1, 
        limit: int = 20,
        mime_type: Optional[str] = None
    ) -> List[Asset]:
        """List assets with pagination and filtering"""
        query = select(Asset)
        
        if mime_type:
            query = query.where(Asset.mime_type == mime_type)
        
        query = query.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_assets(self, query: str) -> List[Asset]:
        """Search assets using full-text search"""
        search_query = select(Asset).where(
            Asset.filename.ilike(f"%{query}%")
        )
        result = await self.db.execute(search_query)
        return result.scalars().all()
```

### 11. Security Standards

#### Input Validation
```python
# models/asset.py
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class AssetCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., regex=r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*$')
    file_size: int = Field(..., gt=0, le=100_000_000)  # Max 100MB
    context: Optional[str] = Field(None, max_length=1000)
    
    @validator('filename')
    def validate_filename(cls, v):
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Filename contains invalid characters')
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        if v > 100_000_000:  # 100MB
            raise ValueError('File size too large')
        return v
```

#### Authentication & Authorization
```python
# middleware/auth.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def require_permission(permission: str):
    """Require specific permission"""
    def permission_checker(current_user: str = Depends(get_current_user)):
        # Check if user has required permission
        if not user_has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return permission_checker
```

### 12. Monitoring & Observability

#### Metrics Collection
```python
# utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from functools import wraps

# Metrics
REQUEST_COUNT = Counter('dataflux_requests_total', 'Total requests', ['service', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('dataflux_request_duration_seconds', 'Request duration', ['service', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('dataflux_active_connections', 'Active connections')

def track_metrics(service_name: str, endpoint: str):
    """Decorator to track request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(service=service_name, endpoint=endpoint, status='success').inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(service=service_name, endpoint=endpoint, status='error').inc()
                raise
            finally:
                REQUEST_DURATION.labels(service=service_name, endpoint=endpoint).observe(time.time() - start_time)
        return wrapper
    return decorator
```

#### Health Checks
```python
# health.py
from fastapi import APIRouter, Depends
from typing import Dict, Any
from .services.asset_service import AssetService
from .external.database import DatabaseClient
from .external.redis import RedisClient

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check(
    db: DatabaseClient = Depends(get_database),
    redis: RedisClient = Depends(get_redis)
) -> Dict[str, Any]:
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        await db.ping()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        await redis.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status
```

## 🎯 Code Review Checklist

### Vor dem Commit
- [ ] Code folgt den Naming Conventions
- [ ] Dateien sind unter der Größen-Limite
- [ ] Alle Tests bestehen
- [ ] Code ist dokumentiert
- [ ] Error Handling ist implementiert
- [ ] Logging ist hinzugefügt
- [ ] Performance ist berücksichtigt

### Code Review
- [ ] Architektur-Prinzipien werden befolgt
- [ ] Separation of Concerns ist eingehalten
- [ ] Dependency Injection ist korrekt
- [ ] Tests sind aussagekräftig
- [ ] Security ist berücksichtigt
- [ ] Performance ist optimiert
- [ ] Code ist wartbar

### Nach dem Merge
- [ ] Monitoring ist konfiguriert
- [ ] Dokumentation ist aktualisiert
- [ ] Deployment ist getestet
- [ ] Rollback-Plan ist vorhanden

## 🚀 Deployment Standards

### Environment Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  dataflux-ingestion:
    build: ./services/ingestion-service
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### Kubernetes Deployment
```yaml
# k8s/ingestion-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataflux-ingestion
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dataflux-ingestion
  template:
    metadata:
      labels:
        app: dataflux-ingestion
    spec:
      containers:
      - name: ingestion
        image: dataflux/ingestion:latest
        ports:
        - containerPort: 8002
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dataflux-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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
```

Dieses Manifest stellt sicher, dass alle zukünftigen Implementierungen konsistent, wartbar und erweiterbar sind, während sie den etablierten Architektur-Prinzipien folgen.