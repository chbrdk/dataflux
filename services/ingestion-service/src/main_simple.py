#!/usr/bin/env python3
"""
DataFlux Ingestion Service - Simplified Version
FastAPI service for file upload and processing without Kafka
"""

import os
import asyncpg
import aioredis
import structlog
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import (
    FastAPI, File, UploadFile, Form, HTTPException, Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import mimetypes
import json
from PIL import Image

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
    thumbnail_path: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None

class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total: int
    page: int
    limit: int

class StatusUpdate(BaseModel):
    status: str

# Thumbnail generation functions
async def generate_thumbnail(image_path: str, thumbnail_path: str, size: tuple = (300, 200)) -> Dict[str, Any]:
    """Generate thumbnail from image file"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNGs with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create thumbnail using Pillow's thumbnail method (maintains aspect ratio)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
            
            return {
                'success': True,
                'thumbnail_path': thumbnail_path,
                'dimensions': img.size,
                'generated': True
            }
    
    except Exception as e:
        logger.error("Failed to generate thumbnail", error=str(e), image_path=image_path)
        return {
            'success': False,
            'error': str(e),
            'generated': False
        }

async def generate_multiple_thumbnails(image_path: str, base_directory: str, asset_id: str) -> Dict[str, Any]:
    """Generate multiple thumbnail sizes for different use cases"""
    
    # Define thumbnail sizes for different use cases
    thumbnail_sizes = {
        'small': (150, 100),    # Grid view thumbnails
        'medium': (400, 300),   # List view thumbnails  
        'large': (1200, 800)    # Modal background images
    }
    
    generated_thumbnails = {}
    
    try:
        os.makedirs(base_directory, exist_ok=True)
        
        # Load original image once
        with Image.open(image_path) as img:
            # Store original dimensions
            original_dimensions = {'width': img.width, 'height': img.height}
            
            for size_name, size in thumbnail_sizes.items():
                # Create thumbnail filename
                thumbnail_filename = f"{asset_id}_{size_name}.jpg"
                thumbnail_path = os.path.join(base_directory, thumbnail_filename)
                
                # Reset image for each thumbnail generation
                img_copy = img.copy()
                
                # Convert to RGB if necessary (for PNGs with transparency)
                if img_copy.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', img_copy.size, (255, 255, 255))
                    if img_copy.mode == 'P':
                        img_copy = img_copy.convert('RGBA')
                    background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode == 'RGBA' else None)
                    img_copy = background
                elif img_copy.mode != 'RGB':
                    img_copy = img_copy.convert('RGB')
                
                # Create thumbnail using Pillow's thumbnail method (maintains aspect ratio)
                img_copy.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Adjust quality based on size - larger thumbnails get higher quality
                quality = 95 if size_name == 'large' else (85 if size_name == 'medium' else 80)
                
                # Save thumbnail
                img_copy.save(thumbnail_path, 'JPEG', quality=quality, optimize=True)
                
                generated_thumbnails[size_name] = {
                    'path': thumbnail_path,
                    'filename': thumbnail_filename,
                    'dimensions': img_copy.size,
                    'quality': quality
                }
        
        return {
            'success': True,
            'thumbnails': generated_thumbnails,
            'original_dimensions': original_dimensions,
            'generated': True
        }
    
    except Exception as e:
        logger.error("Failed to generate multiple thumbnails", error=str(e), image_path=image_path)
        return {
            'success': False,
            'error': str(e),
            'generated': False
        }

async def get_image_dimensions(image_path: str) -> Optional[Dict[str, int]]:
    """Get image dimensions"""
    try:
        with Image.open(image_path) as img:
            return {
                'width': img.width,
                'height': img.height
            }
    except Exception as e:
        logger.error("Failed to get image dimensions", error=str(e), image_path=image_path)
        return None

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
        # Insert new entity first to get ID for storage path
        entity_id = await db.fetchval("""
            INSERT INTO entities (entity_type, metadata)
            VALUES ('asset', $1)
            RETURNING id
        """, json.dumps({"upload_context": context}))
        
        # Save file to local storage and calculate hash while streaming
        storage_dir = "/tmp/dataflux_storage"
        thumbnail_dir = "/tmp/dataflux_thumbnails"
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(thumbnail_dir, exist_ok=True)
        storage_path = os.path.join(storage_dir, f"{entity_id}_{file.filename}")
        
        # Read entire file content
        content = await file.read()
        
        # Write to disk with explicit flush
        with open(storage_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        
        # Calculate hash
        import hashlib
        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        
        print(f"🔥 HASH: {file_hash}, SIZE: {file_size}")
        
        # Debug logging
        logger.info(f"File upload: {file.filename}, size: {file_size}, hash: {file_hash}")
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # Generate multiple thumbnails and get dimensions for images
        thumbnail_path = None
        dimensions = None
        
        if mime_type.startswith('image/'):
            # Generate multiple thumbnail sizes
            thumbnails_result = await generate_multiple_thumbnails(storage_path, thumbnail_dir, entity_id)
            if thumbnails_result['success']:
                # Store the medium size thumbnail path for backward compatibility
                thumbnail_path = thumbnails_result['thumbnails']['medium']['path']
                # Store original dimensions from thumbnail generation
                dimensions = thumbnails_result['original_dimensions']
                logger.info(f"Multiple thumbnails generated for asset {entity_id}")
            else:
                thumbnail_path = None
                logger.warning(f"Failed to generate thumbnails: {thumbnails_result['error']}")
                
            # Fallback to single thumbnail generation if multiple failed
            if not thumbnails_result['success']:
                thumbnail_filename = f"thumb_{entity_id}_{file.filename}.jpg"
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                
                thumbnail_result = await generate_thumbnail(storage_path, thumbnail_path)
                if thumbnail_result['success']:
                    thumbnail_path = thumbnail_result['thumbnail_path']
                    logger.info(f"Fallback thumbnail generated: {thumbnail_path}")
                else:
                    thumbnail_path = None
                    logger.warning(f"Failed to generate fallback thumbnail: {thumbnail_result['error']}")
                
                # Get original image dimensions
                dimensions = await get_image_dimensions(storage_path)
        
        # Check for duplicates
        existing_asset = await db.fetchrow(
            "SELECT id, filename FROM assets WHERE file_hash = $1",
            file_hash
        )
        
        if existing_asset:
            logger.info(f"Duplicate file detected: {file_hash}")
            # Delete the newly created entity and file since it's a duplicate
            await db.execute("DELETE FROM entities WHERE id = $1", entity_id)
            os.remove(storage_path)
            
            return AssetResponse(
                id=str(existing_asset['id']),
                filename=existing_asset['filename'],
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                processing_status="completed",
                created_at=datetime.utcnow(),
                thumbnail_path=None,
                dimensions=None
            )
        
        # Update entity metadata with dimensions
        entity_metadata = {"upload_context": context}
        if dimensions:
            entity_metadata["dimensions"] = dimensions
        
        await db.execute("""
            UPDATE entities 
            SET metadata = $1 
            WHERE id = $2
        """, json.dumps(entity_metadata), entity_id)
        
        # Insert new asset with thumbnail_path
        asset_id = await db.fetchval("""
            INSERT INTO assets (id, filename, file_hash, file_size, mime_type, storage_path, thumbnail_path, upload_context, processing_status, processing_priority)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """, entity_id, file.filename, file_hash, file_size, mime_type, storage_path, thumbnail_path, context, "queued", priority)
        
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
            created_at=datetime.utcnow(),
            thumbnail_path=thumbnail_path,
            dimensions=dimensions
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
            SELECT a.id, a.filename, a.file_size, a.mime_type, a.file_hash, a.processing_status, a.thumbnail_path, e.created_at, e.metadata
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
                    created_at=asset['created_at'],
                    thumbnail_path=asset['thumbnail_path'],
                    dimensions=json.loads(asset['metadata']).get('dimensions') if asset['metadata'] else None
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
            SELECT a.id, a.filename, a.file_size, a.mime_type, a.file_hash, a.processing_status, a.thumbnail_path, e.created_at, e.metadata
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
            created_at=asset['created_at'],
            thumbnail_path=asset['thumbnail_path'],
            dimensions=json.loads(asset['metadata']).get('dimensions') if asset['metadata'] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get asset", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get asset: {str(e)}")

# Get thumbnail endpoint
@app.get("/api/v1/assets/{asset_id}/thumbnail")
async def get_thumbnail(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Serve thumbnail for an asset"""
    try:
        # Get asset thumbnail path
        asset = await db.fetchrow("""
            SELECT thumbnail_path, filename, mime_type
            FROM assets
            WHERE id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        thumbnail_path = asset['thumbnail_path']
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            # Return placeholder if no thumbnail exists
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return FileResponse(
            path=thumbnail_path,
            media_type="image/jpeg",
            headers={
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Content-Disposition': f'inline; filename="thumb_{asset["filename"]}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to serve thumbnail", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to serve thumbnail: {str(e)}")

# Get thumbnail endpoint with size parameter
@app.get("/api/v1/assets/{asset_id}/thumbnail/{size}")
async def get_thumbnail_by_size(
    asset_id: str,
    size: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Serve thumbnail for an asset with specific size (small, medium, large)"""
    try:
        # Validate size parameter
        valid_sizes = ['small', 'medium', 'large']
        if size not in valid_sizes:
            raise HTTPException(status_code=400, detail=f"Invalid size. Must be one of: {', '.join(valid_sizes)}")
        
        # Get asset info
        asset = await db.fetchrow("""
            SELECT filename, mime_type, thumbnail_path
            FROM assets
            WHERE id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        thumbnail_dir = "/tmp/dataflux_thumbnails"
        
        # Construct expected thumbnail filename
        thumbnail_filename = f"{asset_id}_{size}.jpg"
        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
        
        # Check if specific size thumbnail exists
        if os.path.exists(thumbnail_path):
            return FileResponse(
                path=thumbnail_path,
                media_type="image/jpeg",
                headers={
                    'Cache-Control': 'public, max-age=7200',  # Cache for 2 hours
                    'Content-Disposition': f'inline; filename="{asset_id}_{size}.jpg"'
                }
            )
        
        # Fallback to default thumbnail if specific size doesn't exist
        default_thumbnail_path = asset['thumbnail_path']
        if default_thumbnail_path and os.path.exists(default_thumbnail_path):
            return FileResponse(
                path=default_thumbnail_path,
                media_type="image/jpeg",
                headers={
                    'Cache-Control': 'public, max-age=7200',
                    'Content-Disposition': f'inline; filename="thumb_{asset["filename"]}"'
                }
            )
        
        # No thumbnail found
        raise HTTPException(status_code=404, detail=f"No thumbnail found for size '{size}'")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to serve thumbnail", error=str(e), asset_id=asset_id, size=size)
        raise HTTPException(status_code=500, detail=f"Failed to serve thumbnail: {str(e)}")

# Generate thumbnail for existing assets endpoint
@app.post("/api/v1/assets/{asset_id}/generate-thumbnail")
async def generate_thumbnail_for_existing_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Generate thumbnail for an existing asset that doesn't have one"""
    try:
        # Get asset info
        asset = await db.fetchrow("""
            SELECT a.storage_path, a.filename, a.mime_type, e.metadata
            FROM assets a
            JOIN entities e ON a.id = e.id
            WHERE a.id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Check if it's an image
        if not asset['mime_type'].startswith('image/'):
            raise HTTPException(status_code=400, detail="Asset is not an image")
        
        storage_path = asset['storage_path']
        if not os.path.exists(storage_path):
            raise HTTPException(status_code=404, detail="Original file not found on disk")
        
        # Generate thumbnail
        thumbnail_dir = "/tmp/dataflux_thumbnails"
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        thumbnail_filename = f"thumb_{asset_id}_{asset['filename']}.jpg"
        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
        
        thumbnail_result = await generate_thumbnail(storage_path, thumbnail_path)
        
        if not thumbnail_result['success']:
            raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {thumbnail_result['error']}")
        
        # Get dimensions
        dimensions = await get_image_dimensions(storage_path)
        
        # Update asset with thumbnail path
        await db.execute("""
            UPDATE assets 
            SET thumbnail_path = $1 
            WHERE id = $2
        """, thumbnail_path, asset_id)
        
        # Update entity metadata with dimensions
        if dimensions:
            # Parse metadata if it's a JSON string
            if isinstance(asset['metadata'], str):
                current_metadata = json.loads(asset['metadata'] or '{}')
            else:
                current_metadata = asset['metadata'] or {}
            current_metadata['dimensions'] = dimensions
            
            await db.execute("""
                UPDATE entities 
                SET metadata = $1 
                WHERE id = $2
            """, json.dumps(current_metadata), asset_id)
        
        logger.info(f"Generated thumbnail for asset {asset_id}: {thumbnail_path}")
        
        return {
            "success": True,
            "thumbnail_path": thumbnail_path,
            "dimensions": dimensions,
            "message": "Thumbnail generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate thumbnail for existing asset", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {str(e)}")


@app.post("/api/v1/assets/{asset_id}/generate-thumbnails-multiple")
async def generate_multiple_thumbnails_for_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Generate multiple thumbnail sizes for an existing asset"""
    try:
        # Get asset info
        asset = await db.fetchrow("""
            SELECT a.storage_path, a.filename, a.mime_type, e.metadata
            FROM assets a
            JOIN entities e ON a.id = e.id
            WHERE a.id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Check if it's an image
        if not asset['mime_type'].startswith('image/'):
            raise HTTPException(status_code=400, detail="Asset is not an image")
        
        storage_path = asset['storage_path']
        if not os.path.exists(storage_path):
            raise HTTPException(status_code=404, detail="Original file not found")
        
        # Generate multiple thumbnails
        thumbnail_dir = "/tmp/dataflux_thumbnails"
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        thumbnails_result = await generate_multiple_thumbnails(
            storage_path, thumbnail_dir, asset_id
        )
        
        if not thumbnails_result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate thumbnails: {thumbnails_result['error']}"
            )
        
        # Update asset with medium thumbnail path
        medium_path = thumbnails_result['thumbnails']['medium']['path']
        await db.execute("""
            UPDATE assets SET thumbnail_path = $1 WHERE id = $2
        """, medium_path, asset_id)
        
        # Update entity metadata with dimensions
        dimensions = thumbnails_result['original_dimensions']
        if dimensions:
            if isinstance(asset['metadata'], str):
                current_metadata = json.loads(asset['metadata'] or '{}')
            else:
                current_metadata = asset['metadata'] or {}
            current_metadata['dimensions'] = dimensions
            
            await db.execute("""
                UPDATE entities SET metadata = $1 WHERE id = $2
            """, json.dumps(current_metadata), asset_id)
        
        logger.info(f"Generated multiple thumbnails for asset {asset_id}")
        
        return {
            "success": True,
            "thumbnails": {
                size: data['path']
                for size, data in thumbnails_result['thumbnails'].items()
            },
            "dimensions": dimensions,
            "message": "Multiple thumbnails generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to generate multiple thumbnails for asset",
            error=str(e),
            asset_id=asset_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate multiple thumbnails: {str(e)}"
        )

# Bulk generate thumbnails endpoint
@app.post("/api/v1/assets/generate-thumbnails")
async def bulk_generate_thumbnails(
    db: asyncpg.Connection = Depends(get_db)
):
    """Generate thumbnails for all existing image assets that don't have thumbnails"""
    try:
        # Get all image assets without thumbnails
        assets = await db.fetch("""
            SELECT a.id, a.filename, a.storage_path, a.mime_type, e.metadata
            FROM assets a
            JOIN entities e ON a.id = e.id
            WHERE a.mime_type LIKE 'image/%' 
            AND (a.thumbnail_path IS NULL OR a.thumbnail_path = '')
        """)
        
        results = []
        success_count = 0
        error_count = 0
        
        for asset in assets:
            try:
                storage_path = asset['storage_path']
                if not os.path.exists(storage_path):
                    results.append({
                        "asset_id": str(asset['id']),
                        "filename": asset['filename'],
                        "status": "error",
                        "message": "Original file not found on disk"
                    })
                    error_count += 1
                    continue
                
                # Generate thumbnail
                thumbnail_dir = "/tmp/dataflux_thumbnails"
                os.makedirs(thumbnail_dir, exist_ok=True)
                
                thumbnail_filename = f"thumb_{asset['id']}_{asset['filename']}.jpg"
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                
                thumbnail_result = await generate_thumbnail(storage_path, thumbnail_path)
                
                if not thumbnail_result['success']:
                    results.append({
                        "asset_id": str(asset['id']),
                        "filename": asset['filename'],
                        "status": "error",
                        "message": thumbnail_result['error']
                    })
                    error_count += 1
                    continue
                
                # Get dimensions
                dimensions = await get_image_dimensions(storage_path)
                
                # Update asset with thumbnail path
                await db.execute("""
                    UPDATE assets 
                    SET thumbnail_path = $1 
                    WHERE id = $2
                """, thumbnail_path, asset['id'])
                
                # Update entity metadata with dimensions
                if dimensions:
                    # Parse metadata if it's a JSON string
                    if isinstance(asset['metadata'], str):
                        current_metadata = json.loads(asset['metadata'] or '{}')
                    else:
                        current_metadata = asset['metadata'] or {}
                    current_metadata['dimensions'] = dimensions
                    
                    await db.execute("""
                        UPDATE entities 
                        SET metadata = $1 
                        WHERE id = $2
                    """, json.dumps(current_metadata), asset['id'])
                
                results.append({
                    "asset_id": str(asset['id']),
                    "filename": asset['filename'],
                    "status": "success",
                    "thumbnail_path": thumbnail_path,
                    "dimensions": dimensions
                })
                success_count += 1
                
                logger.info(f"Generated thumbnail for asset {asset['id']}: {thumbnail_path}")
                
            except Exception as e:
                results.append({
                    "asset_id": str(asset['id']),
                    "filename": asset['filename'],
                    "status": "error",
                    "message": str(e)
                })
                error_count += 1
                logger.error(f"Failed to generate thumbnail for asset {asset['id']}", error=str(e))
        
        logger.info(f"Bulk thumbnail generation completed: {success_count} success, {error_count} errors")
        
        return {
            "success": True,
            "total_processed": len(assets),
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }
        
    except Exception as e:
        logger.error("Bulk thumbnail generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Bulk thumbnail generation failed: {str(e)}")

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
        
        # Get features for this asset (both direct and segment-based)
        features = await db.fetch("""
            SELECT f.*
            FROM features f
            WHERE f.asset_id = $1
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

# Download asset file endpoint
@app.get("/api/v1/assets/{asset_id}/download")
async def download_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Download asset file"""
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
        
        storage_path = asset['storage_path']
        if not os.path.exists(storage_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Read file and return as bytes directly (avoid FileResponse bug)
        with open(storage_path, "rb") as f:
            file_data = f.read()
        
        from fastapi.responses import Response
        return Response(
            content=file_data,
            media_type=asset['mime_type'],
            headers={
                'Content-Disposition': f'attachment; filename="{asset["filename"]}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download asset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Delete asset endpoint
@app.delete("/api/v1/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: asyncpg.Connection = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Delete asset and all associated data"""
    try:
        # Get asset info before deletion
        asset = await db.fetchrow("""
            SELECT storage_path, filename, thumbnail_path
            FROM assets
            WHERE id = $1
        """, asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Delete from database in correct order
        # First delete embeddings (via entity_id CASCADE)
        # Then delete features and segments (via asset_id)
        # Then delete assets and entities
        
        await db.execute("""
            DELETE FROM features WHERE asset_id = $1
        """, asset_id)
        
        await db.execute("""
            DELETE FROM segments WHERE asset_id = $1
        """, asset_id)
        
        await db.execute("""
            DELETE FROM assets WHERE id = $1
        """, asset_id)
        
        # Delete entity (this will cascade to embeddings)
        await db.execute("""
            DELETE FROM entities WHERE id = $1
        """, asset_id)
        
        # Delete file from disk
        storage_path = asset['storage_path']
        thumbnail_path = asset['thumbnail_path']
        
        if os.path.exists(storage_path):
            os.remove(storage_path)
            logger.info(f"Deleted file from disk: {storage_path}")
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            logger.info(f"Deleted thumbnail from disk: {thumbnail_path}")
        
        # Delete from Redis cache
        await redis.delete(f"asset:{asset_id}")
        
        logger.info("Asset deleted successfully", asset_id=asset_id, filename=asset['filename'])
        
        return {
            "success": True,
            "message": f"Asset {asset['filename']} deleted successfully",
            "asset_id": asset_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error("Failed to delete asset", error=str(e), asset_id=asset_id, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Bulk delete assets endpoint
@app.post("/api/v1/assets/bulk-delete")
async def bulk_delete_assets(
    asset_ids: List[str],
    db: asyncpg.Connection = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Delete multiple assets at once"""
    try:
        deleted_count = 0
        errors = []
        
        for asset_id in asset_ids:
            try:
                # Get asset info
                asset = await db.fetchrow("""
                    SELECT storage_path, filename, thumbnail_path
                    FROM assets
                    WHERE id = $1
                """, asset_id)
                
                if not asset:
                    errors.append({"asset_id": asset_id, "error": "Asset not found"})
                    continue
                
                # Delete from database in correct order (features first due to FK constraint)
                await db.execute("DELETE FROM features WHERE asset_id = $1", asset_id)
                await db.execute("DELETE FROM segments WHERE asset_id = $1", asset_id)
                await db.execute("DELETE FROM assets WHERE id = $1", asset_id)
                await db.execute("DELETE FROM entities WHERE id = $1", asset_id)  # CASCADE to embeddings
                
                # Delete file from disk
                storage_path = asset['storage_path']
                thumbnail_path = asset['thumbnail_path']
                
                if os.path.exists(storage_path):
                    os.remove(storage_path)
                
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                
                # Delete from Redis
                await redis.delete(f"asset:{asset_id}")
                
                deleted_count += 1
                logger.info(f"Deleted asset {asset_id}")
                
            except Exception as e:
                errors.append({"asset_id": asset_id, "error": str(e)})
                logger.error(f"Failed to delete asset {asset_id}", error=str(e))
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "total_requested": len(asset_ids),
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error("Bulk delete failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,  # Direct app object, not string
        host="0.0.0.0",
        port=2013,
        reload=False  # Disable reload to avoid caching issues
    )