#!/usr/bin/env python3
"""
DataFlux Analysis Service
AI-powered media content analysis with Kafka consumer and plugin architecture
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import asyncpg
import aiokafka
from aiokafka import AIOKafkaConsumer
from minio import Minio
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import httpx

# Add analyzers to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from analyzers.base import BaseAnalyzer
from analyzers.video_analyzer import VideoAnalyzer
from analyzers.image_analyzer import ImageAnalyzer
from analyzers.audio_analyzer import AudioAnalyzer
from analyzers.document_analyzer import DocumentAnalyzer

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dataflux_user:dataflux_pass@localhost:2001/dataflux")
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:2009")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:2003")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:2002")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:2005")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:2008")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "dataflux_pass")

# Metrics
PROCESSED_ASSETS = Counter('dataflux_processed_assets_total', 'Total processed assets', ['analyzer_type', 'status'])
PROCESSING_TIME = Histogram('dataflux_processing_duration_seconds', 'Processing time per asset', ['analyzer_type'])
QUEUE_SIZE = Gauge('dataflux_queue_size', 'Current queue size')
ACTIVE_WORKERS = Gauge('dataflux_active_workers', 'Number of active workers')

# Logging setup
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

class AnalysisService:
    """Main analysis service with Kafka consumer and plugin architecture"""
    
    def __init__(self):
        self.db_pool = None
        self.kafka_consumer = None
        self.minio_client = None
        self.http_client = None
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.running = False
        
        # Initialize analyzers
        self._init_analyzers()
        
    def _init_analyzers(self):
        """Initialize all available analyzers"""
        try:
            self.analyzers = {
                'video': VideoAnalyzer(),
                'image': ImageAnalyzer(),
                'audio': AudioAnalyzer(),
                'document': DocumentAnalyzer(),
            }
            logger.info("Analyzers initialized", analyzers=list(self.analyzers.keys()))
        except Exception as e:
            logger.error("Failed to initialize analyzers", error=str(e))
            raise
    
    async def start(self):
        """Start the analysis service"""
        logger.info("Starting DataFlux Analysis Service")
        
        # Start metrics server
        start_http_server(8004)
        logger.info("Metrics server started on port 8004")
        
        # Initialize connections
        await self._init_connections()
        
        # Start Kafka consumer
        await self._start_kafka_consumer()
        
        self.running = True
        logger.info("Analysis service started successfully")
        
        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the analysis service"""
        logger.info("Stopping analysis service")
        self.running = False
        
        if self.kafka_consumer:
            await self.kafka_consumer.stop()
        
        if self.db_pool:
            await self.db_pool.close()
        
        if self.http_client:
            await self.http_client.aclose()
        
        logger.info("Analysis service stopped")
    
    async def _init_connections(self):
        """Initialize database and service connections"""
        try:
            # Database connection
            self.db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=5,
                max_size=20
            )
            logger.info("Database connection established")
            
            # MinIO client
            self.minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False
            )
            logger.info("MinIO client initialized")
            
            # HTTP client
            self.http_client = httpx.AsyncClient(timeout=30.0)
            logger.info("HTTP client initialized")
            
        except Exception as e:
            logger.error("Failed to initialize connections", error=str(e))
            raise
    
    async def _start_kafka_consumer(self):
        """Start Kafka consumer for asset processing"""
        try:
            self.kafka_consumer = AIOKafkaConsumer(
                'asset-processing',
                bootstrap_servers=KAFKA_BROKERS,
                group_id='analysis-service',
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            await self.kafka_consumer.start()
            logger.info("Kafka consumer started")
            
            # Start processing loop
            asyncio.create_task(self._process_messages())
            
        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise
    
    async def _process_messages(self):
        """Process messages from Kafka"""
        logger.info("Starting message processing loop")
        
        async for message in self.kafka_consumer:
            try:
                await self._process_asset(message.value)
            except Exception as e:
                logger.error("Failed to process message", error=str(e), message=message.value)
    
    async def _process_asset(self, message: Dict[str, Any]):
        """Process a single asset"""
        asset_id = message.get('asset_id')
        mime_type = message.get('mime_type')
        priority = message.get('priority', 5)
        
        if not asset_id:
            logger.warning("Received message without asset_id", message=message)
            return
        
        logger.info("Processing asset", asset_id=asset_id, mime_type=mime_type, priority=priority)
        
        # Update processing status
        await self._update_processing_status(asset_id, 'processing')
        
        try:
            # Determine analyzer type
            analyzer_type = self._get_analyzer_type(mime_type)
            
            if analyzer_type not in self.analyzers:
                logger.warning("No analyzer available for type", analyzer_type=analyzer_type, mime_type=mime_type)
                await self._update_processing_status(asset_id, 'failed', error=f"No analyzer for {analyzer_type}")
                return
            
            # Get asset details
            asset_data = await self._get_asset_data(asset_id)
            if not asset_data:
                logger.error("Asset not found", asset_id=asset_id)
                await self._update_processing_status(asset_id, 'failed', error="Asset not found")
                return
            
            # Download file from MinIO
            file_path = await self._download_file(asset_data)
            
            # Process with analyzer
            start_time = time.time()
            analyzer = self.analyzers[analyzer_type]
            
            ACTIVE_WORKERS.inc()
            
            try:
                results = await analyzer.analyze(file_path, asset_data)
                
                # Store results
                await self._store_analysis_results(asset_id, results)
                
                # Update metrics
                PROCESSING_TIME.labels(analyzer_type=analyzer_type).observe(time.time() - start_time)
                PROCESSED_ASSETS.labels(analyzer_type=analyzer_type, status='success').inc()
                
                # Update status
                await self._update_processing_status(asset_id, 'completed')
                
                logger.info("Asset processed successfully", 
                          asset_id=asset_id, 
                          analyzer_type=analyzer_type,
                          processing_time=time.time() - start_time)
                
            finally:
                ACTIVE_WORKERS.dec()
                
                # Cleanup temporary file
                if os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            logger.error("Failed to process asset", asset_id=asset_id, error=str(e))
            PROCESSED_ASSETS.labels(analyzer_type=analyzer_type, status='failed').inc()
            await self._update_processing_status(asset_id, 'failed', error=str(e))
    
    def _get_analyzer_type(self, mime_type: str) -> str:
        """Determine analyzer type from MIME type"""
        if mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type.startswith('application/pdf') or mime_type.startswith('text/'):
            return 'document'
        else:
            return 'document'  # Default fallback
    
    async def _get_asset_data(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset data from database"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT a.*, e.metadata as entity_metadata
                FROM assets a
                JOIN entities e ON a.id = e.id
                WHERE a.id = $1
            """, asset_id)
            
            if row:
                return dict(row)
            return None
    
    async def _download_file(self, asset_data: Dict[str, Any]) -> str:
        """Download file from MinIO to temporary location"""
        bucket = "dataflux-assets"
        object_name = asset_data['storage_path']
        
        # Create temporary file
        temp_dir = Path("/tmp/dataflux-analysis")
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"{asset_data['id']}_{asset_data['filename']}"
        
        # Download from MinIO
        self.minio_client.fget_object(bucket, object_name, str(temp_file))
        
        return str(temp_file)
    
    async def _store_analysis_results(self, asset_id: str, results: Dict[str, Any]):
        """Store analysis results in database"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Store segments
                for segment in results.get('segments', []):
                    segment_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO segments (
                            id, asset_id, segment_type, start_marker, end_marker,
                            confidence_score, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, segment_id, asset_id, segment['type'], 
                    segment.get('start_time', 0), segment.get('end_time', 0),
                    segment.get('confidence', 0.0), json.dumps(segment.get('metadata', {})))
                
                # Store features
                for feature in results.get('features', []):
                    feature_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO features (
                            id, segment_id, feature_type, feature_domain,
                            confidence_score, feature_data, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, feature_id, feature.get('segment_id'), feature['type'],
                    feature.get('domain', 'general'), feature.get('confidence', 0.0),
                    json.dumps(feature.get('data', {})), json.dumps(feature.get('metadata', {})))
                
                # Store embeddings
                for embedding in results.get('embeddings', []):
                    embedding_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO embeddings (
                            id, entity_id, embedding_type, embedding_model,
                            embedding_vector, dimensions, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, embedding_id, asset_id, embedding['type'],
                    embedding.get('model', 'unknown'), json.dumps(embedding['vector']),
                    len(embedding['vector']), json.dumps(embedding.get('metadata', {})))
                
                logger.info("Analysis results stored", asset_id=asset_id, 
                          segments=len(results.get('segments', [])),
                          features=len(results.get('features', [])),
                          embeddings=len(results.get('embeddings', [])))
    
    async def _update_processing_status(self, asset_id: str, status: str, error: Optional[str] = None):
        """Update asset processing status"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE assets 
                SET processing_status = $1, 
                    updated_at = NOW(),
                    error_message = $2
                WHERE id = $3
            """, status, error, asset_id)
            
            logger.info("Processing status updated", asset_id=asset_id, status=status)

async def main():
    """Main entry point"""
    service = AnalysisService()
    
    try:
        await service.start()
    except Exception as e:
        logger.error("Service failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
