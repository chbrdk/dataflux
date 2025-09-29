# DataFlux Shared Libraries

## 📚 Overview

This directory contains shared libraries, schemas, and types used across all DataFlux services.

## 📁 Structure

```
shared/
├── proto/                # Protocol Buffer definitions
│   ├── dataflux.proto    # Main DataFlux protocol
│   ├── ingestion.proto   # Ingestion service protocol
│   ├── query.proto       # Query service protocol
│   └── analysis.proto    # Analysis service protocol
├── schemas/              # JSON schemas and validation
│   ├── asset.json        # Asset schema
│   ├── segment.json      # Segment schema
│   ├── feature.json      # Feature schema
│   └── api/              # API request/response schemas
└── types/                # Type definitions
    ├── python/           # Python type definitions
    ├── go/               # Go type definitions
    ├── typescript/       # TypeScript type definitions
    └── rust/             # Rust type definitions
```

## 🔧 Usage

### Python Services
```python
# Import shared types
from shared.types.python.asset import Asset, AssetStatus
from shared.types.python.segment import Segment, SegmentType

# Use in service
asset = Asset(
    id="asset-123",
    filename="video.mp4",
    status=AssetStatus.QUEUED
)
```

### Go Services
```go
// Import shared types
import "dataflux/shared/types/go/asset"
import "dataflux/shared/types/go/segment"

// Use in service
asset := asset.Asset{
    ID: "asset-123",
    Filename: "video.mp4",
    Status: asset.StatusQueued,
}
```

### TypeScript Services
```typescript
// Import shared types
import { Asset, AssetStatus } from '../shared/types/typescript/asset';
import { Segment, SegmentType } from '../shared/types/typescript/segment';

// Use in service
const asset: Asset = {
    id: 'asset-123',
    filename: 'video.mp4',
    status: AssetStatus.QUEUED
};
```

## 📋 Type Definitions

### Asset Types
- **Asset**: Core asset structure
- **AssetStatus**: Processing status enum
- **AssetMetadata**: Additional metadata
- **UploadContext**: Upload context information

### Segment Types
- **Segment**: Segment structure
- **SegmentType**: Type of segment (scene, paragraph, etc.)
- **TimeMarker**: Time-based markers
- **SpatialMarker**: Spatial markers

### Feature Types
- **Feature**: Extracted feature
- **FeatureDomain**: Domain of feature (visual, audio, etc.)
- **FeatureData**: Feature-specific data
- **ConfidenceScore**: Confidence scoring

### API Types
- **SearchRequest**: Search query structure
- **SearchResponse**: Search results
- **UploadRequest**: File upload request
- **AnalysisResult**: Analysis output

## 🔄 Protocol Buffers

### Definition Example
```protobuf
// shared/proto/dataflux.proto
syntax = "proto3";

package dataflux;

message Asset {
  string id = 1;
  string filename = 2;
  string file_hash = 3;
  int64 file_size = 4;
  string mime_type = 5;
  AssetStatus status = 6;
  int32 priority = 7;
  string created_at = 8;
}

enum AssetStatus {
  QUEUED = 0;
  PROCESSING = 1;
  COMPLETED = 2;
  FAILED = 3;
}
```

### Code Generation
```bash
# Generate Python code
protoc --python_out=shared/types/python/ shared/proto/*.proto

# Generate Go code
protoc --go_out=shared/types/go/ shared/proto/*.proto

# Generate TypeScript code
protoc --ts_out=shared/types/typescript/ shared/proto/*.proto
```

## 📊 JSON Schemas

### Asset Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "filename": {
      "type": "string",
      "minLength": 1
    },
    "file_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$"
    },
    "file_size": {
      "type": "integer",
      "minimum": 0
    },
    "mime_type": {
      "type": "string",
      "pattern": "^[a-z]+/[a-z0-9\\-+]+$"
    },
    "status": {
      "type": "string",
      "enum": ["queued", "processing", "completed", "failed"]
    }
  },
  "required": ["id", "filename", "file_hash", "file_size", "mime_type", "status"]
}
```

### Validation
```python
# Python validation example
import jsonschema
from shared.schemas.asset import asset_schema

def validate_asset(asset_data):
    try:
        jsonschema.validate(asset_data, asset_schema)
        return True
    except jsonschema.ValidationError as e:
        print(f"Validation error: {e.message}")
        return False
```

## 🔄 Versioning

### Semantic Versioning
- **Major**: Breaking changes to API
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, backward compatible

### Migration Strategy
1. **Deprecation**: Mark old types as deprecated
2. **Dual Support**: Support both old and new versions
3. **Migration**: Provide migration tools
4. **Removal**: Remove deprecated types after grace period

## 📝 Contributing

### Adding New Types
1. Define in Protocol Buffers
2. Generate language-specific types
3. Add JSON schema validation
4. Update documentation
5. Add tests
6. Submit pull request

### Type Guidelines
- Use descriptive names
- Include comprehensive documentation
- Follow language conventions
- Add validation rules
- Consider backward compatibility

## 🧪 Testing

### Type Tests
```python
# Python type tests
def test_asset_creation():
    asset = Asset(
        id="test-123",
        filename="test.mp4",
        file_hash="abc123",
        file_size=1024,
        mime_type="video/mp4",
        status=AssetStatus.QUEUED
    )
    assert asset.id == "test-123"
    assert asset.status == AssetStatus.QUEUED
```

### Schema Validation Tests
```python
# Schema validation tests
def test_asset_schema_validation():
    valid_asset = {
        "id": "test-123",
        "filename": "test.mp4",
        "file_hash": "a" * 64,
        "file_size": 1024,
        "mime_type": "video/mp4",
        "status": "queued"
    }
    assert validate_asset(valid_asset) == True
```

## 📋 Checklist

- [ ] Protocol Buffer definitions complete
- [ ] Language-specific types generated
- [ ] JSON schemas defined
- [ ] Validation rules implemented
- [ ] Documentation updated
- [ ] Tests written
- [ ] Version compatibility maintained
- [ ] Migration tools provided
- [ ] CI/CD integration working
- [ ] Code generation automated
