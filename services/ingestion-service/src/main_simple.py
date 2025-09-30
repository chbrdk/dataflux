#!/usr/bin/env python3
"""
DataFlux Ingestion Service - Simplified Version
FastAPI service for file upload and processing without Kafka
"""

import os
import asyncio
import asyncpg
import aioredis
import structlog
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import mimetypes
import json

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
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

logger = structlog.get_logger()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux")
REDIS_URL = os.getenv("REDIS_URL", "redis://default:secure_redis_password_here@localhost:2002/0")

# Initialize FastAPI app
app = FastAPI(
    title="DataFlux Ingestion Service",
    version="1.0.0",
    description="Simplified ingestion service for DataFlux media processing"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None

# Pydantic models
class AssetResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    mime_type: str
    file_hash: str
    processing_status: str
    created_at: datetime

class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total: int
    page: int
    limit: int

class StatusUpdate(BaseModel):
    status: str

# Dependency functions
async def get_db():
    """Get database connection"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    async with db_pool.acquire() as conn:
        yield conn

async def get_redis():
    """Get Redis client"""
    if redis_client is None:
        raise HTTPException(status_code=500, detail="Redis not initialized")
    yield redis_client

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global db_pool, redis_client
    
    # Initialize database pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    logger.info("✅ Database pool initialized")
    
    # Initialize Redis client
    redis_client = aioredis.from_url(REDIS_URL, encoding="utf-8")
    logger.info("✅ Redis client initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    global db_pool, redis_client
    
    if db_pool:
        await db_pool.close()
        logger.info("✅ Database pool closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("✅ Redis client closed")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        
        # Check Redis connection
        if redis_client:
            await redis_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",
                "redis": "connected"
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")

# Asset upload endpoint
@app.post("/api/v1/assets", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    context: str = Form(""),
    priority: int = Form(5),
    db: asyncpg.Connection = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Upload a new asset for processing"""
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Generate file hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # Check for duplicates
        existing_asset = await db.fetchrow(
            "SELECT id FROM assets WHERE file_hash = $1",
            file_hash
        )
        
        if existing_asset:
            logger.info("Duplicate file detected", hash=file_hash)
            return AssetResponse(
                id=str(existing_asset['id']),
                filename=file.filename,
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                processing_status="completed",
                created_at=datetime.utcnow()
            )
        
        # Insert new entity first
        entity_id = await db.fetchval("""
            INSERT INTO entities (entity_type, metadata)
            VALUES ('asset', $1)
            RETURNING id
        """, json.dumps({"upload_context": context}))
        
        # Insert new asset
        asset_id = await db.fetchval("""
            INSERT INTO assets (id, filename, file_hash, file_size, mime_type, storage_path, upload_context, processing_status, processing_priority)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """, entity_id, file.filename, file_hash, file_size, mime_type, f"/storage/{file_hash}", context, "queued", priority)
        
        # Cache in Redis
        await redis.setex(f"asset:{asset_id}", 3600, json.dumps({
            'id': str(asset_id),
            'filename': file.filename,
            'status': 'queued',
            'created_at': datetime.utcnow().isoformat()
        }))
        
        logger.info("Asset uploaded successfully", asset_id=str(asset_id), filename=file.filename)
        
        return AssetResponse(
            id=str(asset_id),
            filename=file.filename,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            processing_status="queued",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# List assets endpoint
@app.get("/api/v1/assets", response_model=AssetListResponse)
async def list_assets(
    page: int = 1,
    limit: int = 20,
    mime_type: str = None,
    status: str = None,
    db: asyncpg.Connection = Depends(get_db)
):
    """List assets with pagination and filters"""
    try:
        # Build query
        where_conditions = []
        params = []
        
        if mime_type:
            where_conditions.append("mime_type LIKE $%d" % (len(params) + 1))
            params.append(mime_type)
        
        if status:
            where_conditions.append("processing_status = $%d" % (len(params) + 1))
            params.append(status)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM assets a JOIN entities e ON a.id = e.id {where_clause.replace('assets', 'a')}"
        total = await db.fetchval(count_query, *params)
        
        # Get assets
        offset = (page - 1) * limit
        assets_query = f"""
            SELECT a.id, a.filename, a.file_size, a.mime_type, a.file_hash, a.processing_status, e.created_at
            FROM assets a
            JOIN entities e ON a.id = e.id
            {where_clause.replace('assets', 'a')}
            ORDER BY e.created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        params.extend([limit, offset])
        
        assets = await db.fetch(assets_query, *params)
        
        return AssetListResponse(
            assets=[
                AssetResponse(
                    id=str(asset['id']),
                    filename=asset['filename'],
                    file_size=asset['file_size'],
                    mime_type=asset['mime_type'],
                    file_hash=asset['file_hash'],
                    processing_status=asset['processing_status'],
                    created_at=asset['created_at']
                )
                for asset in assets
            ],
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list assets", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list assets: {str(e)}")

# Update asset status endpoint
@app.put("/api/v1/assets/{asset_id}/status")
async def update_asset_status(
    asset_id: str,
    status_update: StatusUpdate,
    db: asyncpg.Connection = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Update asset processing status"""
    try:
        new_status = status_update.status
        
        # Update asset status in database
        await db.execute("""
            UPDATE assets 
            SET processing_status = $1
            WHERE id = $2
        """, new_status, asset_id)
        
        # Update Redis cache
        await redis.setex(f"asset:{asset_id}", 3600, json.dumps({
            'id': asset_id,
            'status': new_status
        }))
        
        logger.info("Asset status updated", asset_id=asset_id, status=new_status)
        
        return {"message": f"Asset {asset_id} status updated to {new_status}"}
        
    except Exception as e:
        logger.error("Failed to update asset status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Get asset details endpoint
@app.get("/api/v1/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get asset details by ID"""
    try:
        asset = await db.fetchrow("""
            SELECT a.id, a.filename, a.file_size, a.mime_type, a.file_hash, a.processing_status, e.created_at
            FROM assets a
            JOIN entities e ON a.id = e.id
            WHERE a.id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        return AssetResponse(
            id=str(asset['id']),
            filename=asset['filename'],
            file_size=asset['file_size'],
            mime_type=asset['mime_type'],
            file_hash=asset['file_hash'],
            processing_status=asset['processing_status'],
            created_at=asset['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get asset", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get asset: {str(e)}")

# Analysis results endpoint
@app.get("/api/v1/assets/{asset_id}/analysis")
async def get_asset_analysis(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get analysis results for an asset"""
    try:
        # Get asset info
        asset = await db.fetchrow("""
            SELECT a.*, e.created_at
            FROM assets a
            JOIN entities e ON a.id = e.id
            WHERE a.id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Get segments for this asset
        segments = await db.fetch("""
            SELECT s.*
            FROM segments s
            WHERE s.asset_id = $1
            ORDER BY s.sequence_number
        """, asset_id)
        
        # Get features for this asset
        features = await db.fetch("""
            SELECT f.*
            FROM features f
            JOIN segments s ON f.segment_id = s.id
            WHERE s.asset_id = $1
            ORDER BY f.confidence DESC
        """, asset_id)
        
        # Format results
        analysis_results = {
            "asset_id": str(asset_id),
            "filename": asset['filename'],
            "mime_type": asset['mime_type'],
            "processing_status": asset['processing_status'],
            "segments": [],
            "features": [],
            "summary": {
                "total_segments": len(segments),
                "total_features": len(features),
                "analysis_completed": asset['processing_status'] == 'completed'
            }
        }
        
        # Process segments
        for segment in segments:
            segment_data = {
                "id": str(segment['id']),
                "type": segment['segment_type'],
                "sequence_number": segment['sequence_number'],
                "start_marker": segment['start_marker'] if segment['start_marker'] else {},
                "end_marker": segment['end_marker'] if segment['end_marker'] else {},
                "confidence": float(segment['confidence_score']) if segment['confidence_score'] else None,
                "duration": float(segment['duration']) if segment['duration'] else None
            }
            analysis_results["segments"].append(segment_data)
        
        # Process features
        for feature in features:
            feature_data = {
                "id": str(feature['id']),
                "type": feature['feature_type'],
                "domain": feature['feature_domain'],
                "confidence": float(feature['confidence']) if feature['confidence'] else None,
                "data": feature['feature_data'] if feature['feature_data'] else {},
                "analyzer_version": feature['analyzer_version'],
                "created_at": feature['created_at'].isoformat() if feature['created_at'] else None
            }
            analysis_results["features"].append(feature_data)
        
        return analysis_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analysis results", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=2013,
        reload=True
    )