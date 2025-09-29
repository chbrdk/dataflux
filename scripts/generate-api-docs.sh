#!/bin/bash
# DataFlux API Documentation Generator
# Generates interactive API documentation from OpenAPI specification

set -euo pipefail

# Configuration
DOCS_DIR="docs/api"
OPENAPI_FILE="$DOCS_DIR/openapi.yaml"
OUTPUT_DIR="$DOCS_DIR/generated"
TEMPLATE_DIR="$DOCS_DIR/templates"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Create output directory
create_output_dir() {
    log "Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
}

# Generate HTML documentation
generate_html_docs() {
    log "Generating HTML documentation..."
    
    if command -v redoc-cli &> /dev/null; then
        redoc-cli build "$OPENAPI_FILE" --output "$OUTPUT_DIR/index.html" --title "DataFlux API Documentation"
        log "✓ HTML documentation generated"
    else
        log_warn "redoc-cli not found, installing..."
        npm install -g redoc-cli
        redoc-cli build "$OPENAPI_FILE" --output "$OUTPUT_DIR/index.html" --title "DataFlux API Documentation"
        log "✓ HTML documentation generated"
    fi
}

# Generate Markdown documentation
generate_markdown_docs() {
    log "Generating Markdown documentation..."
    
    if command -v swagger-codegen &> /dev/null; then
        swagger-codegen generate -i "$OPENAPI_FILE" -l markdown -o "$OUTPUT_DIR/markdown"
        log "✓ Markdown documentation generated"
    else
        log_warn "swagger-codegen not found, using custom generator"
        generate_custom_markdown
    fi
}

# Custom Markdown generator
generate_custom_markdown() {
    log "Generating custom Markdown documentation..."
    
    local markdown_file="$OUTPUT_DIR/api-reference.md"
    
    cat > "$markdown_file" << 'EOF'
# DataFlux API Reference

## Overview

DataFlux ist eine Universal AI-native Database für Medieninhalte mit einer Plugin-Architektur und Multi-Modal Search Capabilities.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.dataflux.com`

## Authentication

All API endpoints (except `/health` and `/docs`) require authentication via JWT tokens.

### Getting Access Token

```bash
curl -X POST http://localhost:8006/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Using Access Token

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8003/api/v1/search
```

## Endpoints

### Authentication

#### POST /auth/login
Authenticate user and receive JWT tokens.

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "role": "user"
}
```

### Assets

#### POST /api/v1/assets
Upload a new media asset.

**Request Body (multipart/form-data):**
- `file`: Media file to upload
- `collection_id`: Collection ID (optional)
- `priority`: Processing priority (low, normal, high)
- `metadata`: Additional metadata as JSON string

**Response:**
```json
{
  "asset_id": "123e4567-e89b-12d3-a456-426614174000",
  "file_name": "sample_video.mp4",
  "file_size": 1048576,
  "mime_type": "video/mp4",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/v1/assets
List assets with pagination and filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `collection_id`: Filter by collection
- `mime_type`: Filter by MIME type
- `status`: Filter by status

#### GET /api/v1/assets/{asset_id}
Get detailed information about a specific asset.

### Search

#### POST /api/v1/search
Multi-modal search across all media types.

**Request Body:**
```json
{
  "query": "cat playing with ball",
  "query_type": "text",
  "filters": {
    "mime_type": "video/%",
    "min_confidence": 0.7
  },
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "asset_id": "123e4567-e89b-12d3-a456-426614174000",
      "file_name": "cat_video.mp4",
      "similarity_score": 0.95,
      "thumbnail_path": "/thumbnails/cat_video.jpg"
    }
  ],
  "total": 1,
  "query_time": 150
}
```

#### POST /api/v1/similar
Find assets similar to a given asset.

**Request Body:**
```json
{
  "asset_id": "123e4567-e89b-12d3-a456-426614174000",
  "limit": 5,
  "threshold": 0.8
}
```

### Analysis

#### GET /api/v1/analysis/{asset_id}
Get AI analysis results for an asset.

**Response:**
```json
{
  "asset_id": "123e4567-e89b-12d3-a456-426614174000",
  "analysis_status": "completed",
  "segments": [
    {
      "segment_id": "456e7890-e89b-12d3-a456-426614174000",
      "segment_type": "scene",
      "start_time": 0.0,
      "end_time": 5.0,
      "confidence_score": 0.9
    }
  ],
  "features": [
    {
      "feature_id": "789e0123-e89b-12d3-a456-426614174000",
      "feature_type": "object",
      "feature_data": {"object": "cat", "confidence": 0.95}
    }
  ]
}
```

### Collections

#### GET /api/v1/collections
List user's collections.

#### POST /api/v1/collections
Create a new collection.

**Request Body:**
```json
{
  "name": "My Collection",
  "description": "Collection description"
}
```

### Monitoring

#### GET /health
Check system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "postgresql": "healthy",
    "redis": "healthy",
    "kafka": "healthy",
    "minio": "healthy",
    "weaviate": "healthy",
    "neo4j": "healthy"
  }
}
```

#### GET /api/v1/stats
Get system usage statistics.

**Response:**
```json
{
  "total_assets": 1000,
  "total_collections": 50,
  "total_users": 25,
  "storage_used": 1073741824,
  "processing_queue": 5,
  "system_uptime": 86400
}
```

## Error Handling

### Error Response Format

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid input parameters",
  "details": {
    "field": "file",
    "reason": "File size exceeds limit"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common Error Codes

- **400 Bad Request**: Invalid input parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: System error
- **503 Service Unavailable**: Service down

## Rate Limiting

API requests are rate limited to prevent abuse:

- **Authentication**: 10 requests per minute
- **Asset Upload**: 100 requests per hour
- **Search**: 1000 requests per hour
- **General API**: 10000 requests per hour

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## SDKs and Examples

### Python SDK Example

```python
import requests

class DataFluxClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.token = self._authenticate(username, password)
    
    def _authenticate(self, username, password):
        response = requests.post(f"{self.base_url}/auth/login", json={
            "username": username,
            "password": password
        })
        return response.json()["access_token"]
    
    def upload_asset(self, file_path, collection_id=None):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'collection_id': collection_id} if collection_id else {}
            response = requests.post(
                f"{self.base_url}/api/v1/assets",
                files=files,
                data=data,
                headers={'Authorization': f'Bearer {self.token}'}
            )
        return response.json()
    
    def search(self, query, query_type="text", limit=20):
        response = requests.post(
            f"{self.base_url}/api/v1/search",
            json={
                "query": query,
                "query_type": query_type,
                "limit": limit
            },
            headers={'Authorization': f'Bearer {self.token}'}
        )
        return response.json()

# Usage
client = DataFluxClient("http://localhost:8000", "admin", "admin123")
result = client.upload_asset("video.mp4")
search_results = client.search("cat playing")
```

### JavaScript SDK Example

```javascript
class DataFluxClient {
    constructor(baseUrl, username, password) {
        this.baseUrl = baseUrl;
        this.token = null;
        this.authenticate(username, password);
    }
    
    async authenticate(username, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        this.token = data.access_token;
    }
    
    async uploadAsset(file, collectionId = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (collectionId) {
            formData.append('collection_id', collectionId);
        }
        
        const response = await fetch(`${this.baseUrl}/api/v1/assets`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`
            },
            body: formData
        });
        return await response.json();
    }
    
    async search(query, queryType = 'text', limit = 20) {
        const response = await fetch(`${this.baseUrl}/api/v1/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
                query,
                query_type: queryType,
                limit
            })
        });
        return await response.json();
    }
}

// Usage
const client = new DataFluxClient('http://localhost:8000', 'admin', 'admin123');
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];
const result = await client.uploadAsset(file);
const searchResults = await client.search('cat playing');
```

## Testing

### Postman Collection

A Postman collection is available for testing the API:

1. Import the collection from `docs/api/postman/DataFlux-API.postman_collection.json`
2. Set the environment variables:
   - `base_url`: `http://localhost:8000`
   - `username`: `admin`
   - `password`: `admin123`
3. Run the collection to test all endpoints

### cURL Examples

```bash
# Login
curl -X POST http://localhost:8006/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Upload asset
curl -X POST http://localhost:8002/api/v1/assets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@video.mp4" \
  -F "collection_id=123e4567-e89b-12d3-a456-426614174000"

# Search
curl -X POST http://localhost:8003/api/v1/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"cat playing","limit":10}'

# Get asset details
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8002/api/v1/assets/123e4567-e89b-12d3-a456-426614174000
```

## Changelog

### Version 1.0.0
- Initial API release
- Multi-modal search capabilities
- Asset management
- User authentication
- Collection management
- Analysis results
- System monitoring

## Support

For API support and questions:
- **Documentation**: Check this API reference
- **Examples**: Review SDK examples
- **Community**: Post questions in community forum
- **Support**: Contact technical support
EOF

    log "✓ Custom Markdown documentation generated"
}

# Generate Postman collection
generate_postman_collection() {
    log "Generating Postman collection..."
    
    local postman_file="$OUTPUT_DIR/DataFlux-API.postman_collection.json"
    
    cat > "$postman_file" << 'EOF'
{
  "info": {
    "name": "DataFlux API",
    "description": "DataFlux API collection for testing",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "type": "string"
    },
    {
      "key": "username",
      "value": "admin",
      "type": "string"
    },
    {
      "key": "password",
      "value": "admin123",
      "type": "string"
    },
    {
      "key": "access_token",
      "value": "",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{username}}\",\n  \"password\": \"{{password}}\"\n}"
            },
            "url": {
              "raw": "{{base_url}}/auth/login",
              "host": ["{{base_url}}"],
              "path": ["auth", "login"]
            }
          },
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "if (pm.response.code === 200) {",
                  "    const response = pm.response.json();",
                  "    pm.collectionVariables.set('access_token', response.access_token);",
                  "}"
                ]
              }
            }
          ]
        }
      ]
    },
    {
      "name": "Assets",
      "item": [
        {
          "name": "Upload Asset",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{access_token}}"
              }
            ],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "file",
                  "type": "file",
                  "src": "sample_video.mp4"
                },
                {
                  "key": "collection_id",
                  "value": "123e4567-e89b-12d3-a456-426614174000",
                  "type": "text"
                }
              ]
            },
            "url": {
              "raw": "{{base_url}}/api/v1/assets",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "assets"]
            }
          }
        },
        {
          "name": "List Assets",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{access_token}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/api/v1/assets?page=1&limit=20",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "assets"],
              "query": [
                {
                  "key": "page",
                  "value": "1"
                },
                {
                  "key": "limit",
                  "value": "20"
                }
              ]
            }
          }
        }
      ]
    },
    {
      "name": "Search",
      "item": [
        {
          "name": "Text Search",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{access_token}}"
              },
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"query\": \"cat playing with ball\",\n  \"query_type\": \"text\",\n  \"limit\": 10\n}"
            },
            "url": {
              "raw": "{{base_url}}/api/v1/search",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "search"]
            }
          }
        }
      ]
    },
    {
      "name": "Monitoring",
      "item": [
        {
          "name": "Health Check",
          "request": {
            "method": "GET",
            "url": {
              "raw": "{{base_url}}/health",
              "host": ["{{base_url}}"],
              "path": ["health"]
            }
          }
        }
      ]
    }
  ]
}
EOF

    log "✓ Postman collection generated"
}

# Generate SDK examples
generate_sdk_examples() {
    log "Generating SDK examples..."
    
    local sdk_dir="$OUTPUT_DIR/sdk"
    mkdir -p "$sdk_dir"
    
    # Python SDK
    cat > "$sdk_dir/python_client.py" << 'EOF'
#!/usr/bin/env python3
"""
DataFlux Python SDK
Simple client for interacting with DataFlux API
"""

import requests
import json
from typing import Optional, Dict, Any, List

class DataFluxClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.token = self._authenticate(username, password)
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
    
    def _authenticate(self, username: str, password: str) -> str:
        """Authenticate and get access token"""
        response = self.session.post(f"{self.base_url}/auth/login", json={
            "username": username,
            "password": password
        })
        response.raise_for_status()
        return response.json()["access_token"]
    
    def upload_asset(self, file_path: str, collection_id: Optional[str] = None, 
                    priority: str = "normal", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Upload a media asset"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'priority': priority
            }
            if collection_id:
                data['collection_id'] = collection_id
            if metadata:
                data['metadata'] = json.dumps(metadata)
            
            response = self.session.post(
                f"{self.base_url}/api/v1/assets",
                files=files,
                data=data
            )
        response.raise_for_status()
        return response.json()
    
    def list_assets(self, page: int = 1, limit: int = 20, 
                    collection_id: Optional[str] = None,
                    mime_type: Optional[str] = None) -> Dict[str, Any]:
        """List assets with pagination and filtering"""
        params = {
            'page': page,
            'limit': limit
        }
        if collection_id:
            params['collection_id'] = collection_id
        if mime_type:
            params['mime_type'] = mime_type
        
        response = self.session.get(f"{self.base_url}/api/v1/assets", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Get asset details"""
        response = self.session.get(f"{self.base_url}/api/v1/assets/{asset_id}")
        response.raise_for_status()
        return response.json()
    
    def search(self, query: str, query_type: str = "text", 
               filters: Optional[Dict] = None, limit: int = 20) -> Dict[str, Any]:
        """Search across media assets"""
        payload = {
            "query": query,
            "query_type": query_type,
            "limit": limit
        }
        if filters:
            payload["filters"] = filters
        
        response = self.session.post(
            f"{self.base_url}/api/v1/search",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def find_similar(self, asset_id: str, limit: int = 10, 
                    threshold: float = 0.7) -> Dict[str, Any]:
        """Find similar assets"""
        response = self.session.post(
            f"{self.base_url}/api/v1/similar",
            json={
                "asset_id": asset_id,
                "limit": limit,
                "threshold": threshold
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_analysis(self, asset_id: str) -> Dict[str, Any]:
        """Get analysis results for an asset"""
        response = self.session.get(f"{self.base_url}/api/v1/analysis/{asset_id}")
        response.raise_for_status()
        return response.json()
    
    def create_collection(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new collection"""
        response = self.session.post(
            f"{self.base_url}/api/v1/collections",
            json={
                "name": name,
                "description": description
            }
        )
        response.raise_for_status()
        return response.json()
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List user's collections"""
        response = self.session.get(f"{self.base_url}/api/v1/collections")
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        response = self.session.get(f"{self.base_url}/api/v1/stats")
        response.raise_for_status()
        return response.json()

# Example usage
if __name__ == "__main__":
    # Initialize client
    client = DataFluxClient("http://localhost:8000", "admin", "admin123")
    
    # Check system health
    health = client.health_check()
    print(f"System status: {health['status']}")
    
    # Upload a file
    result = client.upload_asset("sample_video.mp4", metadata={"tags": ["demo", "test"]})
    print(f"Uploaded asset: {result['asset_id']}")
    
    # Search for content
    search_results = client.search("cat playing", limit=5)
    print(f"Found {len(search_results['results'])} results")
    
    # Get system stats
    stats = client.get_stats()
    print(f"Total assets: {stats['total_assets']}")
EOF

    # JavaScript SDK
    cat > "$sdk_dir/javascript_client.js" << 'EOF'
/**
 * DataFlux JavaScript SDK
 * Simple client for interacting with DataFlux API
 */

class DataFluxClient {
    constructor(baseUrl, username, password) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.token = null;
        this.authenticate(username, password);
    }
    
    async authenticate(username, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error(`Authentication failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        this.token = data.access_token;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                ...options.headers
            },
            ...options
        };
        
        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`Request failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async uploadAsset(file, collectionId = null, priority = 'normal', metadata = null) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('priority', priority);
        
        if (collectionId) {
            formData.append('collection_id', collectionId);
        }
        
        if (metadata) {
            formData.append('metadata', JSON.stringify(metadata));
        }
        
        return await this.request('/api/v1/assets', {
            method: 'POST',
            body: formData
        });
    }
    
    async listAssets(page = 1, limit = 20, collectionId = null, mimeType = null) {
        const params = new URLSearchParams({
            page: page.toString(),
            limit: limit.toString()
        });
        
        if (collectionId) {
            params.append('collection_id', collectionId);
        }
        
        if (mimeType) {
            params.append('mime_type', mimeType);
        }
        
        return await this.request(`/api/v1/assets?${params}`);
    }
    
    async getAsset(assetId) {
        return await this.request(`/api/v1/assets/${assetId}`);
    }
    
    async search(query, queryType = 'text', filters = null, limit = 20) {
        const payload = {
            query,
            query_type: queryType,
            limit
        };
        
        if (filters) {
            payload.filters = filters;
        }
        
        return await this.request('/api/v1/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
    }
    
    async findSimilar(assetId, limit = 10, threshold = 0.7) {
        return await this.request('/api/v1/similar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                asset_id: assetId,
                limit,
                threshold
            })
        });
    }
    
    async getAnalysis(assetId) {
        return await this.request(`/api/v1/analysis/${assetId}`);
    }
    
    async createCollection(name, description = null) {
        return await this.request('/api/v1/collections', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                description
            })
        });
    }
    
    async listCollections() {
        return await this.request('/api/v1/collections');
    }
    
    async healthCheck() {
        return await this.request('/health');
    }
    
    async getStats() {
        return await this.request('/api/v1/stats');
    }
}

// Example usage
async function example() {
    try {
        // Initialize client
        const client = new DataFluxClient('http://localhost:8000', 'admin', 'admin123');
        
        // Check system health
        const health = await client.healthCheck();
        console.log(`System status: ${health.status}`);
        
        // Upload a file
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];
        const result = await client.uploadAsset(file, null, 'normal', { tags: ['demo', 'test'] });
        console.log(`Uploaded asset: ${result.asset_id}`);
        
        // Search for content
        const searchResults = await client.search('cat playing', 'text', null, 5);
        console.log(`Found ${searchResults.results.length} results`);
        
        // Get system stats
        const stats = await client.getStats();
        console.log(`Total assets: ${stats.total_assets}`);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataFluxClient;
}
EOF

    log "✓ SDK examples generated"
}

# Generate API documentation index
generate_index() {
    log "Generating documentation index..."
    
    local index_file="$OUTPUT_DIR/README.md"
    
    cat > "$index_file" << 'EOF'
# DataFlux API Documentation

This directory contains the generated API documentation for DataFlux.

## Available Documentation

### Interactive Documentation
- **[HTML Documentation](index.html)** - Interactive API documentation with Swagger UI
- **[OpenAPI Specification](openapi.yaml)** - Complete OpenAPI 3.0 specification

### Reference Documentation
- **[API Reference](api-reference.md)** - Complete API reference in Markdown format
- **[SDK Examples](sdk/)** - Client SDK examples in Python and JavaScript
- **[Postman Collection](DataFlux-API.postman_collection.json)** - Postman collection for testing

## Quick Start

### 1. Authentication
```bash
curl -X POST http://localhost:8006/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 2. Upload Asset
```bash
curl -X POST http://localhost:8002/api/v1/assets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@video.mp4"
```

### 3. Search
```bash
curl -X POST http://localhost:8003/api/v1/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"cat playing","limit":10}'
```

## SDK Usage

### Python
```python
from sdk.python_client import DataFluxClient

client = DataFluxClient("http://localhost:8000", "admin", "admin123")
result = client.upload_asset("video.mp4")
search_results = client.search("cat playing")
```

### JavaScript
```javascript
import DataFluxClient from './sdk/javascript_client.js';

const client = new DataFluxClient('http://localhost:8000', 'admin', 'admin123');
const result = await client.uploadAsset(file);
const searchResults = await client.search('cat playing');
```

## Testing

### Postman
1. Import `DataFlux-API.postman_collection.json` into Postman
2. Set environment variables:
   - `base_url`: `http://localhost:8000`
   - `username`: `admin`
   - `password`: `admin123`
3. Run the collection to test all endpoints

### cURL
See the [API Reference](api-reference.md) for detailed cURL examples.

## Support

For API support and questions:
- **Documentation**: Check this API reference
- **Examples**: Review SDK examples
- **Community**: Post questions in community forum
- **Support**: Contact technical support
EOF

    log "✓ Documentation index generated"
}

# Main function
main() {
    log "Starting API documentation generation..."
    
    # Create output directory
    create_output_dir
    
    # Generate documentation
    generate_html_docs
    generate_markdown_docs
    generate_postman_collection
    generate_sdk_examples
    generate_index
    
    log "API documentation generation completed successfully!"
    log "Generated files:"
    log "  - HTML Documentation: $OUTPUT_DIR/index.html"
    log "  - Markdown Reference: $OUTPUT_DIR/api-reference.md"
    log "  - Postman Collection: $OUTPUT_DIR/DataFlux-API.postman_collection.json"
    log "  - SDK Examples: $OUTPUT_DIR/sdk/"
    log "  - Documentation Index: $OUTPUT_DIR/README.md"
}

# Handle script arguments
case "${1:-}" in
    "generate")
        main
        ;;
    "html")
        create_output_dir
        generate_html_docs
        ;;
    "markdown")
        create_output_dir
        generate_markdown_docs
        ;;
    "postman")
        create_output_dir
        generate_postman_collection
        ;;
    "sdk")
        create_output_dir
        generate_sdk_examples
        ;;
    "index")
        create_output_dir
        generate_index
        ;;
    *)
        echo "Usage: $0 {generate|html|markdown|postman|sdk|index}"
        echo ""
        echo "Commands:"
        echo "  generate  - Generate all documentation"
        echo "  html      - Generate HTML documentation only"
        echo "  markdown  - Generate Markdown documentation only"
        echo "  postman   - Generate Postman collection only"
        echo "  sdk       - Generate SDK examples only"
        echo "  index     - Generate documentation index only"
        exit 1
        ;;
esac
