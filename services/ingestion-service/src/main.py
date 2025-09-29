"""
DataFlux Ingestion Service
FastAPI service for file upload, deduplication, and processing queue management
"""

import os
import hashlib
import uuid
import json
import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

import asyncpg
import aioredis
import aiokafka
# import magic  # Commented out due to libmagic dependency
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from minio import Minio
from minio.error import S3Error

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux")
REDIS_URL = os.getenv("REDIS_URL", "redis://default:secure_redis_password_here@localhost:2002/0")
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:2009")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:2003")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "secure_minio_password_here")

# Initialize FastAPI app
app = FastAPI(
    title="DataFlux Ingestion Service",
    version="1.0.0",
    description="File upload and processing queue management for DataFlux",
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
    priority: int = Field(5, ge=1, le=10, description="Processing priority (1=high, 10=low)")
    collection_id: Optional[str] = Field(None, description="Collection UUID")

class AssetResponse(BaseModel):
    id: str
    filename: str
    file_hash: str
    file_size: int
    mime_type: str
    status: str
    created_at: datetime
    processing_eta: Optional[int] = None
    duplicate: bool = False

class AssetDetail(BaseModel):
    id: str
    filename: str
    file_hash: str
    file_size: int
    mime_type: str
    storage_path: str
    processing_status: str
    processing_priority: int
    confidence_score: float
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    segments: List[Dict[str, Any]] = []

class ProcessingStatus(BaseModel):
    asset_id: str
    status: str
    progress: float = 0.0
    message: Optional[str] = None
    updated_at: datetime

# Global variables for connections
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None
kafka_producer: Optional[aiokafka.AIOKafkaProducer] = None
minio_client: Optional[Minio] = None

# Dependency injection functions
async def get_db():
    """Get database connection from pool"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    async with db_pool.acquire() as conn:
        yield conn

async def get_redis():
    """Get Redis client"""
    if redis_client is None:
        raise HTTPException(status_code=500, detail="Redis not initialized")
    yield redis_client

async def get_kafka_producer():
    """Get Kafka producer"""
    if kafka_producer is None:
        raise HTTPException(status_code=500, detail="Kafka not initialized")
    yield kafka_producer

def get_minio_client():
    """Get MinIO client"""
    if minio_client is None:
        raise HTTPException(status_code=500, detail="MinIO not initialized")
    return minio_client

# Utility functions
def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def detect_mime_type(content: bytes, filename: str) -> str:
    """Detect MIME type using filename extension"""
    ext = Path(filename).suffix.lower()
    mime_map = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip'
    }
    return mime_map.get(ext, 'application/octet-stream')

def calculate_processing_eta(file_size: int, priority: int) -> int:
    """Calculate estimated processing time in seconds"""
    base_time = file_size / (1024 * 1024)  # 1 second per MB
    priority_multiplier = {1: 0.5, 2: 0.7, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.5, 9: 2.0, 10: 3.0}
    return int(base_time * priority_multiplier.get(priority, 1.0))

async def check_duplicate(file_hash: str, db: asyncpg.Connection) -> Optional[str]:
    """Check if file hash already exists"""
    result = await db.fetchval(
        "SELECT id FROM assets WHERE file_hash = $1",
        file_hash
    )
    return result

async def store_asset_metadata(
    asset_id: str,
    filename: str,
    file_hash: str,
    file_size: int,
    mime_type: str,
    storage_path: str,
    context: Optional[str],
    priority: int,
    collection_id: Optional[str],
    db: asyncpg.Connection
) -> None:
    """Store asset metadata in database"""
    now = datetime.utcnow()
    
    # Insert into entities table
    await db.execute("""
        INSERT INTO entities (id, entity_type, parent_id, created_at, updated_at, metadata)
        VALUES ($1, 'asset', $2, $3, $4, $5)
    """, asset_id, collection_id, now, now, json.dumps({"context": context}))
    
    # Insert into assets table
    await db.execute("""
        INSERT INTO assets (
            id, filename, file_hash, file_size, mime_type,
            storage_path, upload_context, processing_status,
            processing_priority, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    """, asset_id, filename, file_hash, file_size, mime_type,
        storage_path, context, "queued", priority, now)

async def store_file_in_minio(
    bucket: str,
    object_name: str,
    content: bytes,
    mime_type: str,
    minio_client: Minio
) -> None:
    """Store file in MinIO object storage"""
    try:
        # Ensure bucket exists
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
        
        # Upload file
        minio_client.put_object(
            bucket,
            object_name,
            io.BytesIO(content),
            len(content),
            content_type=mime_type
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {str(e)}")

async def publish_processing_message(
    asset_id: str,
    mime_type: str,
    priority: int,
    kafka_producer: aiokafka.AIOKafkaProducer
) -> None:
    """Publish asset processing message to Kafka"""
    message = {
        "asset_id": asset_id,
        "mime_type": mime_type,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ingestion"
    }
    
    await kafka_producer.send_and_wait(
        "asset-processing",
        json.dumps(message).encode()
    )

async def cache_asset_status(
    asset_id: str,
    status: str,
    filename: str,
    redis_client: aioredis.Redis
) -> None:
    """Cache asset status in Redis"""
    cache_data = {
        "status": status,
        "filename": filename,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    await redis_client.setex(
        f"asset:{asset_id}",
        3600,  # 1 hour TTL
        json.dumps(cache_data)
    )

# API Endpoints
@app.post("/api/v1/assets", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    metadata: AssetUpload = Depends(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: asyncpg.Connection = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    kafka: aiokafka.AIOKafkaProducer = Depends(get_kafka_producer)
):
    """
    Upload and queue an asset for processing
    
    - **file**: The file to upload
    - **context**: Optional user-provided context
    - **priority**: Processing priority (1=high, 10=low)
    - **collection_id**: Optional collection UUID
    """
    
    # Read file content
    content = await file.read()
    file_hash = calculate_file_hash(content)
    mime_type = detect_mime_type(content, file.filename)
    
    # Check for duplicates
    existing_id = await check_duplicate(file_hash, db)
    if existing_id:
        # Return existing asset info
        existing_asset = await db.fetchrow(
            "SELECT * FROM assets WHERE id = $1",
            existing_id
        )
        
        return AssetResponse(
            id=str(existing_asset['id']),
            filename=existing_asset['filename'],
            file_hash=existing_asset['file_hash'],
            file_size=existing_asset['file_size'],
            mime_type=existing_asset['mime_type'],
            status=existing_asset['processing_status'],
            created_at=existing_asset['created_at'],
            duplicate=True
        )
    
    # Generate UUID and storage path
    asset_id = str(uuid.uuid4())
    bucket = "dataflux-assets"
    object_name = f"{asset_id}/{file.filename}"
    
    # Store file in MinIO
    minio_client = get_minio_client()
    await store_file_in_minio(bucket, object_name, content, mime_type, minio_client)
    
    # Store metadata in database
    await store_asset_metadata(
        asset_id, file.filename, file_hash, len(content),
        mime_type, object_name, metadata.context,
        metadata.priority, metadata.collection_id, db
    )
    
    # Publish to Kafka queue
    await publish_processing_message(asset_id, mime_type, metadata.priority, kafka)
    
    # Cache status in Redis
    await cache_asset_status(asset_id, "queued", file.filename, redis)
    
    # Calculate ETA
    eta = calculate_processing_eta(len(content), metadata.priority)
    
    return AssetResponse(
        id=asset_id,
        filename=file.filename,
        file_hash=file_hash,
        file_size=len(content),
        mime_type=mime_type,
        status="queued",
        created_at=datetime.utcnow(),
        processing_eta=eta,
        duplicate=False
    )

@app.get("/api/v1/assets/{asset_id}", response_model=AssetDetail)
async def get_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get asset details including segments"""
    
    # Get asset details
    asset = await db.fetchrow("""
        SELECT a.*, e.created_at, e.updated_at, e.metadata
        FROM assets a
        JOIN entities e ON a.id = e.id
        WHERE a.id = $1
    """, asset_id)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get segments
    segments = await db.fetch("""
        SELECT s.*, e.created_at, e.updated_at, e.metadata
        FROM segments s
        JOIN entities e ON s.id = e.id
        WHERE s.asset_id = $1
        ORDER BY s.sequence_number
    """, asset_id)
    
    return AssetDetail(
        id=str(asset['id']),
        filename=asset['filename'],
        file_hash=asset['file_hash'],
        file_size=asset['file_size'],
        mime_type=asset['mime_type'],
        storage_path=asset['storage_path'],
        processing_status=asset['processing_status'],
        processing_priority=asset['processing_priority'],
        confidence_score=asset['confidence_score'],
        created_at=asset['created_at'],
        updated_at=asset['updated_at'],
        metadata=json.loads(asset['metadata']) if asset['metadata'] else {},
        segments=[dict(segment) for segment in segments]
    )

@app.get("/api/v1/assets", response_model=List[AssetResponse])
async def list_assets(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    mime_type: Optional[str] = None,
    db: asyncpg.Connection = Depends(get_db)
):
    """List assets with pagination and filtering"""
    
    offset = (page - 1) * limit
    where_clause = "WHERE 1=1"
    params = [offset, limit]
    param_count = 2
    
    if status:
        param_count += 1
        where_clause += f" AND a.processing_status = ${param_count}"
        params.append(status)
    
    if mime_type:
        param_count += 1
        where_clause += f" AND a.mime_type = ${param_count}"
        params.append(mime_type)
    
    assets = await db.fetch(f"""
        SELECT a.*, e.created_at
        FROM assets a
        JOIN entities e ON a.id = e.id
        {where_clause}
        ORDER BY e.created_at DESC
        OFFSET $1 LIMIT $2
    """, *params)
    
    return [
        AssetResponse(
            id=str(asset['id']),
            filename=asset['filename'],
            file_hash=asset['file_hash'],
            file_size=asset['file_size'],
            mime_type=asset['mime_type'],
            status=asset['processing_status'],
            created_at=asset['created_at']
        )
        for asset in assets
    ]

@app.get("/api/v1/assets/{asset_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    asset_id: str,
    redis: aioredis.Redis = Depends(get_redis),
    db: asyncpg.Connection = Depends(get_db)
):
    """Get current processing status of an asset"""
    
    # Try Redis cache first
    cached = await redis.get(f"asset:{asset_id}")
    if cached:
        cache_data = json.loads(cached)
        return ProcessingStatus(
            asset_id=asset_id,
            status=cache_data['status'],
            message=f"Last updated: {cache_data['updated_at']}"
        )
    
    # Fallback to database
    asset = await db.fetchrow(
        "SELECT processing_status FROM assets WHERE id = $1",
        asset_id
    )
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return ProcessingStatus(
        asset_id=asset_id,
        status=asset['processing_status'],
        updated_at=datetime.utcnow()
    )

@app.post("/api/v1/assets/{asset_id}/analyze")
async def trigger_reanalysis(
    asset_id: str,
    force: bool = False,
    priority: int = 5,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: asyncpg.Connection = Depends(get_db),
    kafka: aiokafka.AIOKafkaProducer = Depends(get_kafka_producer)
):
    """Trigger re-analysis of an asset"""
    
    # Check if asset exists
    asset = await db.fetchrow(
        "SELECT * FROM assets WHERE id = $1",
        asset_id
    )
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if not force and asset['processing_status'] == 'processing':
        raise HTTPException(status_code=409, detail="Asset is already being processed")
    
    # Update status to queued
    await db.execute(
        "UPDATE assets SET processing_status = 'queued', processing_priority = $1 WHERE id = $2",
        priority, asset_id
    )
    
    # Publish to Kafka
    await publish_processing_message(asset_id, asset['mime_type'], priority, kafka)
    
    return {"message": "Re-analysis triggered", "asset_id": asset_id}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": "ingestion-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
    
    # Check database connection
    try:
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["database"] = "connected"
        else:
            health_status["database"] = "not_initialized"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
    
    # Check Redis connection
    try:
        if redis_client:
            await redis_client.ping()
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "not_initialized"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
    
    # Check Kafka connection
    try:
        if kafka_producer:
            health_status["kafka"] = "connected"
        else:
            health_status["kafka"] = "not_initialized"
    except Exception as e:
        health_status["kafka"] = f"error: {str(e)}"
    
    # Check MinIO connection
    try:
        if minio_client:
            minio_client.list_buckets()
            health_status["minio"] = "connected"
        else:
            health_status["minio"] = "not_initialized"
    except Exception as e:
        health_status["minio"] = f"error: {str(e)}"
    
    return health_status

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global db_pool, redis_client, kafka_producer, minio_client
    
    # Initialize database pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    
    # Initialize Redis client
    redis_client = aioredis.from_url(REDIS_URL, encoding="utf-8")
    
    # Initialize Kafka producer
    kafka_producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=KAFKA_BROKERS,
        value_serializer=lambda v: v
    )
    await kafka_producer.start()
    
    # Initialize MinIO client
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    # Ensure default bucket exists
    try:
        if not minio_client.bucket_exists("dataflux-assets"):
            minio_client.make_bucket("dataflux-assets")
    except Exception as e:
        print(f"Warning: Could not create bucket: {e}")

@app.put("/api/v1/assets/{asset_id}/status")
async def update_asset_status(
    asset_id: str,
    status_update: dict,
    db: asyncpg.Connection = Depends(get_db)
):
    """Update asset processing status"""
    try:
        new_status = status_update.get('status')
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        # Update asset status in database
        await db.execute("""
            UPDATE assets 
            SET processing_status = $1, updated_at = NOW()
            WHERE id = $2
        """, new_status, asset_id)
        
        # Update Redis cache
        redis = await get_redis()
        await redis.setex(f"asset:{asset_id}", 3600, json.dumps({
            'id': asset_id,
            'status': new_status,
            'updated_at': datetime.utcnow().isoformat()
        }))
        
        return {"message": f"Asset {asset_id} status updated to {new_status}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    global db_pool, redis_client, kafka_producer
    
    if db_pool:
        await db_pool.close()
    
    if redis_client:
        await redis_client.close()
    
    if kafka_producer:
        await kafka_producer.stop()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
