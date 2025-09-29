# DataFlux User Guide

## Getting Started

### What is DataFlux?

DataFlux ist eine **Universal AI-native Database** für Medieninhalte, die es ermöglicht, große Mengen von Videos, Bildern, Audio-Dateien und Dokumenten zu verarbeiten, zu analysieren und durchsuchbar zu machen.

### Key Features

- 🎥 **Multi-Modal Search**: Suche über verschiedene Medientypen hinweg
- 🤖 **AI-Powered Analysis**: Automatische Inhaltsanalyse mit Machine Learning
- 📊 **Real-time Processing**: Streaming und Batch-Verarbeitung
- 🔍 **Semantic Search**: Verstehende Suche nach Inhalt, nicht nur Keywords
- 📈 **Scalable Architecture**: Microservices-basierte Architektur
- 🔒 **Enterprise Security**: JWT Authentication und RBAC

## Quick Start

### 1. Installation

#### Prerequisites
- Docker and Docker Compose
- 8GB RAM minimum (16GB recommended)
- 50GB free disk space

#### Local Development Setup
```bash
# Clone the repository
git clone https://github.com/dataflux/dataflux.git
cd dataflux

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Wait for services to be ready
./scripts/health-check.py

# Access the web interface
open http://localhost:3000
```

### 2. First Login

#### Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

#### Change Default Password
```bash
# Access the web interface
open http://localhost:3000

# Login with default credentials
# Go to Settings > Profile
# Change password to something secure
```

### 3. Upload Your First Asset

#### Via Web Interface
1. Navigate to **Assets** → **Upload**
2. Drag and drop a video file
3. Select a collection (or create new)
4. Click **Upload**
5. Wait for processing to complete

#### Via API
```bash
# Get authentication token
TOKEN=$(curl -X POST http://localhost:8006/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# Upload a file
curl -X POST http://localhost:8002/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_video.mp4" \
  -F "collection_id=your-collection-id"
```

## User Interface Guide

### Dashboard Overview

The DataFlux dashboard provides a comprehensive overview of your media assets and system status.

#### Main Navigation
- **Dashboard**: System overview and statistics
- **Assets**: Asset management and upload
- **Search**: Multi-modal search interface
- **Collections**: Organize assets into collections
- **Analytics**: Usage statistics and insights
- **Settings**: User preferences and system configuration

#### Dashboard Widgets
- **Total Assets**: Number of uploaded assets
- **Processing Queue**: Assets currently being processed
- **Storage Used**: Disk space utilization
- **Recent Activity**: Latest uploads and searches
- **System Health**: Service status indicators

### Asset Management

#### Uploading Assets

##### Supported Formats
- **Video**: MP4, AVI, MOV, MKV, WebM
- **Audio**: MP3, WAV, FLAC, AAC, OGG
- **Images**: JPEG, PNG, GIF, WebP, TIFF
- **Documents**: PDF, DOC, DOCX, TXT, RTF

##### Upload Options
- **Drag & Drop**: Simply drag files to the upload area
- **File Browser**: Click to browse and select files
- **Batch Upload**: Upload multiple files at once
- **URL Import**: Import from web URLs

##### Upload Settings
- **Collection**: Assign to existing or new collection
- **Priority**: Set processing priority (Low, Normal, High)
- **Metadata**: Add custom tags and descriptions
- **Thumbnail**: Generate thumbnail previews

#### Asset Details

##### Asset Information
- **File Name**: Original filename
- **File Size**: Size in bytes
- **MIME Type**: Media type
- **Upload Date**: When the asset was uploaded
- **Processing Status**: Current processing state
- **Hash**: Unique file identifier

##### Analysis Results
- **Segments**: Detected scenes, shots, or sections
- **Features**: Extracted objects, faces, text
- **Embeddings**: Vector representations for search
- **Confidence Scores**: AI analysis confidence levels

##### Asset Actions
- **Download**: Download original file
- **Preview**: View thumbnail or preview
- **Edit Metadata**: Update tags and descriptions
- **Delete**: Remove asset from system
- **Share**: Generate shareable links

### Search Interface

#### Search Types

##### Text Search
```bash
# Search for specific content
"cat playing with ball"
"sunset over mountains"
"business meeting"
```

##### Image Search
- Upload an image to find similar content
- Visual similarity search
- Object and scene recognition

##### Audio Search
- Upload audio file to find similar sounds
- Music and speech recognition
- Audio fingerprinting

##### Video Search
- Upload video to find similar content
- Scene and object matching
- Temporal similarity

#### Search Filters

##### Basic Filters
- **Media Type**: Video, Audio, Image, Document
- **Collection**: Filter by collection
- **Date Range**: Upload date range
- **File Size**: Size range
- **Duration**: For video/audio files

##### Advanced Filters
- **Confidence Score**: Minimum AI confidence
- **Processing Status**: Completed, Processing, Failed
- **Tags**: Custom tags and metadata
- **User**: Who uploaded the asset

#### Search Results

##### Result Display
- **Grid View**: Thumbnail grid layout
- **List View**: Detailed list with metadata
- **Timeline View**: Chronological organization

##### Result Information
- **Similarity Score**: How well the result matches
- **Thumbnail**: Visual preview
- **Metadata**: Tags, descriptions, dates
- **Segments**: Relevant sections within the asset

##### Result Actions
- **View Details**: See full asset information
- **Play Preview**: Preview video/audio
- **Download**: Download the asset
- **Add to Collection**: Organize results

### Collections

#### Creating Collections

##### Collection Types
- **Personal**: Private collections
- **Shared**: Collections shared with team
- **Public**: Collections visible to all users

##### Collection Settings
- **Name**: Descriptive collection name
- **Description**: Collection purpose and content
- **Tags**: Categorization tags
- **Access Level**: Who can view/edit

#### Managing Collections

##### Adding Assets
- **Bulk Add**: Select multiple assets
- **Drag & Drop**: Drag assets to collection
- **API Integration**: Programmatic addition

##### Collection Organization
- **Nested Collections**: Hierarchical organization
- **Smart Collections**: Auto-populated based on criteria
- **Collection Templates**: Reusable collection structures

##### Collection Actions
- **Rename**: Update collection name
- **Move**: Reorganize collection structure
- **Delete**: Remove collection and assets
- **Export**: Download collection as archive

### Analytics

#### Usage Statistics

##### Asset Analytics
- **Total Assets**: Number of uploaded assets
- **Storage Usage**: Disk space consumption
- **Processing Time**: Average processing duration
- **Success Rate**: Processing success percentage

##### Search Analytics
- **Search Queries**: Most common searches
- **Result Clicks**: Most clicked results
- **Search Performance**: Query response times
- **User Behavior**: Search patterns and trends

##### System Analytics
- **API Usage**: API call statistics
- **User Activity**: Active users and sessions
- **Performance Metrics**: System performance data
- **Error Rates**: System error statistics

#### Custom Reports

##### Report Types
- **Asset Reports**: Asset usage and statistics
- **User Reports**: User activity and behavior
- **System Reports**: System performance and health
- **Custom Reports**: User-defined report criteria

##### Report Scheduling
- **Daily Reports**: Automated daily summaries
- **Weekly Reports**: Weekly activity reports
- **Monthly Reports**: Monthly usage statistics
- **Custom Schedule**: User-defined intervals

## API Usage Guide

### Authentication

#### Getting Access Token
```bash
# Login to get JWT token
curl -X POST http://localhost:8006/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Using Access Token
```bash
# Include token in Authorization header
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8003/api/v1/search
```

### Asset Management API

#### Upload Asset
```bash
curl -X POST http://localhost:8002/api/v1/assets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@video.mp4" \
  -F "collection_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "priority=normal" \
  -F "metadata={\"tags\":[\"demo\",\"video\"]}"
```

#### List Assets
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8002/api/v1/assets?page=1&limit=20&mime_type=video/%"
```

#### Get Asset Details
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8002/api/v1/assets/123e4567-e89b-12d3-a456-426614174000
```

### Search API

#### Text Search
```bash
curl -X POST http://localhost:8003/api/v1/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cat playing with ball",
    "query_type": "text",
    "filters": {
      "mime_type": "video/%",
      "min_confidence": 0.7
    },
    "limit": 10
  }'
```

#### Similar Content Search
```bash
curl -X POST http://localhost:8003/api/v1/similar \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "limit": 5,
    "threshold": 0.8
  }'
```

### Analysis API

#### Get Analysis Results
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8004/api/v1/analysis/123e4567-e89b-12d3-a456-426614174000
```

#### Trigger Analysis
```bash
curl -X POST http://localhost:8004/api/v1/analysis/trigger \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "analysis_type": "full"
  }'
```

## Best Practices

### Asset Organization

#### Naming Conventions
- **Descriptive Names**: Use clear, descriptive filenames
- **Consistent Format**: Follow consistent naming patterns
- **Version Control**: Include version numbers when applicable
- **Date Format**: Use ISO date format (YYYY-MM-DD)

#### Tagging Strategy
- **Hierarchical Tags**: Use nested tag structures
- **Consistent Vocabulary**: Maintain consistent tag names
- **Multiple Categories**: Tag with multiple relevant categories
- **Regular Review**: Periodically review and update tags

#### Collection Structure
- **Logical Grouping**: Group related assets together
- **Access Control**: Set appropriate access levels
- **Regular Cleanup**: Remove outdated collections
- **Documentation**: Document collection purposes

### Search Optimization

#### Query Construction
- **Specific Terms**: Use specific, descriptive terms
- **Multiple Keywords**: Combine multiple relevant keywords
- **Boolean Operators**: Use AND, OR, NOT when appropriate
- **Phrase Queries**: Use quotes for exact phrases

#### Filter Usage
- **Relevant Filters**: Apply only relevant filters
- **Date Ranges**: Use date ranges to narrow results
- **Media Types**: Filter by media type when appropriate
- **Confidence Scores**: Set appropriate confidence thresholds

#### Result Evaluation
- **Relevance Assessment**: Evaluate result relevance
- **Feedback Provision**: Provide feedback on search results
- **Result Refinement**: Refine queries based on results
- **Alternative Searches**: Try different search approaches

### Performance Optimization

#### Upload Optimization
- **File Compression**: Compress files before upload
- **Batch Uploads**: Upload multiple files together
- **Off-Peak Uploads**: Upload during off-peak hours
- **Network Optimization**: Use stable network connections

#### Search Performance
- **Cached Queries**: Reuse similar search queries
- **Indexed Fields**: Search on indexed fields
- **Result Limiting**: Limit result sets appropriately
- **Pagination**: Use pagination for large result sets

#### System Monitoring
- **Resource Usage**: Monitor system resource usage
- **Performance Metrics**: Track performance metrics
- **Error Monitoring**: Monitor system errors
- **Capacity Planning**: Plan for capacity growth

## Troubleshooting

### Common Issues

#### Upload Problems

##### File Upload Fails
**Problem**: File upload fails with error message
**Solutions**:
- Check file size limits (default: 100MB)
- Verify file format is supported
- Check network connection stability
- Ensure sufficient disk space

##### Processing Stuck
**Problem**: Asset processing remains in "processing" state
**Solutions**:
- Check system resources (CPU, memory)
- Verify all services are running
- Check processing queue status
- Restart processing service if needed

#### Search Issues

##### No Results Found
**Problem**: Search returns no results
**Solutions**:
- Check search query spelling
- Try broader search terms
- Verify filters are not too restrictive
- Check if assets are properly processed

##### Slow Search Performance
**Problem**: Search queries take too long
**Solutions**:
- Check system resource usage
- Verify database indexes
- Use more specific search terms
- Check cache status

#### Authentication Problems

##### Login Fails
**Problem**: Cannot login with correct credentials
**Solutions**:
- Verify username and password
- Check if account is active
- Verify authentication service is running
- Check system logs for errors

##### Token Expired
**Problem**: API requests fail with token error
**Solutions**:
- Refresh authentication token
- Check token expiration time
- Verify token format
- Re-authenticate if needed

### System Maintenance

#### Regular Maintenance Tasks

##### Daily Tasks
- Check system health status
- Monitor resource usage
- Review error logs
- Verify backup status

##### Weekly Tasks
- Review user activity
- Clean up temporary files
- Update system documentation
- Test disaster recovery procedures

##### Monthly Tasks
- Review system performance
- Update security patches
- Analyze usage statistics
- Plan capacity upgrades

#### Backup and Recovery

##### Backup Verification
```bash
# Verify backup integrity
./scripts/verify-backup.sh automatic

# Test restore procedure
./scripts/recovery.sh interactive
```

##### Data Retention
```bash
# Run data retention cleanup
./scripts/retention.sh run

# Check retention policies
./scripts/retention.sh policies
```

### Getting Help

#### Support Channels
- **Documentation**: Check this user guide
- **API Documentation**: Review OpenAPI specification
- **System Logs**: Check application logs
- **Community Forum**: Post questions and issues

#### Log Locations
- **Application Logs**: `/var/log/dataflux/`
- **System Logs**: `/var/log/syslog`
- **Docker Logs**: `docker logs <container_name>`
- **Service Logs**: `journalctl -u <service_name>`

#### Useful Commands
```bash
# Check system health
./scripts/health-check.py

# View service status
docker-compose -f docker/docker-compose.yml ps

# Check system resources
htop
df -h
free -h

# View recent logs
tail -f /var/log/dataflux/ingestion.log
```

## Advanced Features

### Custom Analyzers

#### Creating Custom Analyzers
```python
from analyzers.base import BaseAnalyzer

class CustomAnalyzer(BaseAnalyzer):
    def get_supported_formats(self):
        return ['application/pdf']
    
    def extract_segments(self, file_path):
        # Custom segment extraction logic
        pass
    
    def analyze_segment(self, segment):
        # Custom analysis logic
        pass
    
    def generate_embeddings(self, content):
        # Custom embedding generation
        pass
```

#### Plugin Registration
```python
# Register custom analyzer
from analysis_service import AnalysisService

service = AnalysisService()
service.register_analyzer(CustomAnalyzer())
```

### API Integration

#### Webhook Integration
```bash
# Configure webhook for asset processing
curl -X POST http://localhost:8002/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["asset.processed", "asset.failed"],
    "secret": "your-webhook-secret"
  }'
```

#### Batch Operations
```bash
# Batch upload multiple files
for file in *.mp4; do
  curl -X POST http://localhost:8002/api/v1/assets \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -F "file=@$file" \
    -F "collection_id=your-collection-id"
done
```

### Performance Tuning

#### Database Optimization
```sql
-- Create performance indexes
CREATE INDEX idx_assets_collection_status ON assets(collection_id, status);
CREATE INDEX idx_segments_asset_type ON segments(asset_id, segment_type);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM assets WHERE collection_id = '123';
```

#### Cache Configuration
```bash
# Configure Redis cache
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

This user guide provides comprehensive information for using DataFlux effectively. For additional help, refer to the API documentation or contact support.
