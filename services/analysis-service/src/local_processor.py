#!/usr/bin/env python3
"""
DataFlux Local Asset Processor
Processes queued assets using the same configuration as ingestion service
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

import aiosqlite

# Configuration - same as ingestion service
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dataflux.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalAssetProcessor:
    """Local asset processor that processes queued assets"""
    
    def __init__(self):
        self.db_url = self._get_local_db_url()
        self.running = False
        
    def _get_local_db_url(self) -> str:
        """Get local database URL - use SQLite"""
        return "dataflux.db"
        
    async def start(self):
        """Start the asset processor"""
        logger.info("Starting Local Asset Processor")
        logger.info(f"Database URL: {self.db_url}")
        
        self.running = True
        
        # Start processing loop
        try:
            while self.running:
                await self._process_queued_assets()
                await asyncio.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Processor failed: {e}")
        finally:
            self.running = False
    
    async def _process_queued_assets(self):
        """Process assets with status 'queued'"""
        try:
            # Get queued assets
            assets = await self._get_queued_assets()
            
            if not assets:
                logger.debug("No queued assets found")
                return
            
            logger.info(f"Found {len(assets)} queued assets")
            
            # Process each asset
            for asset in assets:
                await self._process_single_asset(asset)
                
        except Exception as e:
            logger.error(f"Error processing queued assets: {e}")
    
    async def _get_queued_assets(self) -> List[Dict[str, Any]]:
        """Get assets with status 'queued'"""
        try:
            async with aiosqlite.connect(self.db_url) as db:
                cursor = await db.execute("""
                    SELECT id, filename, file_size, mime_type, created_at
                    FROM assets 
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    LIMIT 5
                """)
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get queued assets: {e}")
            return []
    
    async def _process_single_asset(self, asset: Dict[str, Any]):
        """Process a single asset"""
        asset_id = asset['id']
        filename = asset['filename']
        mime_type = asset['mime_type']
        
        logger.info(f"Processing asset {asset_id}: {filename} ({mime_type})")
        
        try:
            # Update status to processing
            await self._update_asset_status(asset_id, 'processing')
            
            # Simulate processing
            processing_time = await self._simulate_processing(mime_type, asset['file_size'])
            
            # Generate sample analysis data
            await self._generate_analysis_data(asset_id, mime_type)
            
            # Update status to completed
            await self._update_asset_status(asset_id, 'completed')
            
            logger.info(f"Successfully processed asset {asset_id} in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process asset {asset_id}: {e}")
            await self._update_asset_status(asset_id, 'failed', str(e))
    
    async def _simulate_processing(self, mime_type: str, file_size: int) -> float:
        """Simulate processing time"""
        base_time = 2.0
        
        if mime_type.startswith('video/'):
            base_time = 8.0
        elif mime_type.startswith('image/'):
            base_time = 1.0
        elif mime_type.startswith('audio/'):
            base_time = 3.0
        
        # Simulate processing delay (max 5 seconds for demo)
        await asyncio.sleep(min(base_time, 5))
        
        return base_time
    
    async def _generate_analysis_data(self, asset_id: str, mime_type: str):
        """Generate sample analysis data"""
        async with aiosqlite.connect(self.db_url) as db:
            async with db:
                # Insert sample segment
                segment_id = str(uuid.uuid4())
                await db.execute("""
                    INSERT OR IGNORE INTO segments (
                        id, asset_id, segment_type, start_marker, end_marker,
                        confidence_score, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (segment_id, asset_id, 'processed_segment', 0, 10.0, 0.95, 
                json.dumps({
                    'media_type': mime_type,
                    'processed_at': datetime.utcnow().isoformat(),
                    'analysis_version': '1.0'
                })))
                
                # Insert sample feature
                feature_id = str(uuid.uuid4())
                await db.execute("""
                    INSERT OR IGNORE INTO features (
                        id, segment_id, feature_type, feature_domain,
                        confidence_score, feature_data, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (feature_id, segment_id, 'analysis_complete', 'processing',
                1.0, json.dumps({'status': 'completed'}), 
                json.dumps({'asset_id': asset_id})))
                
                await db.commit()
                logger.info(f"Generated analysis data for asset {asset_id}")
    
    async def _update_asset_status(self, asset_id: str, status: str, error: Optional[str] = None):
        """Update asset processing status"""
        try:
            async with aiosqlite.connect(self.db_url) as db:
                await db.execute("""
                    UPDATE assets 
                    SET status = ? 
                    WHERE id = ?
                """, (status, asset_id))
                await db.commit()
                
                logger.info(f"Updated asset {asset_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update asset status: {e}")

async def main():
    """Main entry point"""
    processor = LocalAssetProcessor()
    
    try:
        await processor.start()
    except KeyboardInterrupt:
        logger.info("Processor stopped by user")
    except Exception as e:
        logger.error(f"Processor failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
