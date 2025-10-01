#!/usr/bin/env python3
"""
API-based Asset Processor - kommuniziert direkt mit Ingestion Service
"""

import requests
import json
import time
import logging
import uuid
import os
import asyncio
import asyncpg
from datetime import datetime
from pathlib import Path

# Import analyzers
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from analyzers.image_analyzer import ImageAnalyzer

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIAssetProcessor:
    """Asset processor der über API kommuniziert"""
    
    def __init__(self):
        self.ingestion_url = "http://localhost:2013"
        self.running = False
        
        # Initialize analyzers
        self.image_analyzer = ImageAnalyzer()
        
        # Storage paths
        self.storage_base_path = "/tmp/dataflux_storage"  # Will be configured via environment
        os.makedirs(self.storage_base_path, exist_ok=True)
        
        # Database connection
        self.db_url = "postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux"
        
    def get_queued_assets(self):
        """Hole queued assets vom Ingestion Service"""
        try:
            response = requests.get(f"{self.ingestion_url}/api/v1/assets")
            if response.status_code == 200:
                assets = response.json()
                queued_assets = [asset for asset in assets['assets'] if asset['processing_status'] == 'queued']
                return queued_assets
            else:
                logger.error(f"Failed to get assets: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching assets: {e}")
            return []
    
    def update_asset_status(self, asset_id: str, status: str):
        """Update asset status über API"""
        try:
            response = requests.put(f"{self.ingestion_url}/api/v1/assets/{asset_id}/status", 
                                    json={"status": status})
            
            if response.status_code == 200:
                logger.info(f"📝 Asset {asset_id} Status auf '{status}' aktualisiert")
            else:
                logger.error(f"❌ Status-Update fehlgeschlagen: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
    
    def simulate_processing(self, asset):
        """Simuliere Asset-Verarbeitung"""
        asset_id = asset['id']
        filename = asset['filename']
        mime_type = asset['mime_type']
        
        logger.info(f"🔄 Processing {filename} ({mime_type})")
        
        # Update to processing
        self.update_asset_status(asset_id, 'processing')
        
        # Processing-Zeit basierend auf Dateityp
        if mime_type.startswith('video/'):
            processing_time = 8
        elif mime_type.startswith('image/'):
            processing_time = 1
        elif mime_type.startswith('audio/'):
            processing_time = 3
        else:
            processing_time = 2
        
        logger.info(f"⏱️  Simulating {processing_time}s processing...")
        time.sleep(min(processing_time, 5))  # Max 5 seconds für Demo
        
        # Generiere echte Analyse-Ergebnisse
        asyncio.run(self.generate_analysis_results(asset))
        
        # Mark as completed
        self.update_asset_status(asset_id, 'completed')
        logger.info(f"✅ Completed processing {filename}")
    
    async def generate_analysis_results(self, asset):
        """Generiere echte Analyse-Ergebnisse"""
        asset_id = asset['id']
        filename = asset['filename']
        mime_type = asset['mime_type']
        
        try:
            # Download file from MinIO or local storage
            file_path = await self._download_asset_file(asset)
            if not file_path:
                logger.error(f"Failed to download file for {filename}")
                return self._generate_fallback_results(asset)
            
            # Run appropriate analyzer
            if mime_type.startswith('image/'):
                results = await self.image_analyzer.analyze(file_path, asset)
                logger.info(f"🧠 Image analysis completed for {filename}")
            elif mime_type.startswith('video/'):
                # TODO: Implement video analyzer
                results = self._generate_fallback_results(asset)
                logger.info(f"🧠 Video analysis (fallback) for {filename}")
            elif mime_type.startswith('audio/'):
                # TODO: Implement audio analyzer
                results = self._generate_fallback_results(asset)
                logger.info(f"🧠 Audio analysis (fallback) for {filename}")
            else:
                # TODO: Implement document analyzer
                results = self._generate_fallback_results(asset)
                logger.info(f"🧠 Document analysis (fallback) for {filename}")
            
            # Store results in database
            await self._store_analysis_results(asset_id, results)
            
            # Keep file for now (don't clean up)
            # if os.path.exists(file_path):
            #     os.remove(file_path)
            
            return results
            
        except Exception as e:
            logger.error(f"Analysis failed for {filename}: {e}")
            return self._generate_fallback_results(asset)
    
    async def _download_asset_file(self, asset):
        """Download asset file for analysis"""
        try:
            # Get asset details from Ingestion Service
            asset_id = asset['id']
            filename = asset['filename']
            file_path = os.path.join(self.storage_base_path, f"{asset_id}_{filename}")
            
            # Download file from Ingestion Service
            download_url = f"{self.ingestion_url}/api/v1/assets/{asset_id}/download"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        # Save file to local storage
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        logger.info(f"Downloaded file: {filename} -> {file_path}")
                        return file_path
                    else:
                        logger.error(f"Failed to download file: HTTP {response.status}")
                        return None
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None
    
    def _generate_fallback_results(self, asset):
        """Generate fallback results when real analysis fails"""
        mime_type = asset['mime_type']
        
        if mime_type.startswith('video/'):
            return {
                'segments': [],
                'features': [{
                    'type': 'video_analysis_fallback',
                    'domain': 'visual',
                    'confidence': 0.5,
                    'data': {
                        'status': 'fallback',
                        'objects': ['person', 'building', 'car'],
                        'audio_segments': ['speech', 'music', 'silence']
                    },
                    'metadata': {'analyzer': 'fallback'}
                }],
                'embeddings': [],
                'metadata': {'status': 'fallback', 'analyzer': 'fallback'}
            }
        elif mime_type.startswith('image/'):
            return {
                'segments': [],
                'features': [{
                    'type': 'image_analysis_fallback',
                    'domain': 'visual',
                    'confidence': 0.5,
                    'data': {
                        'status': 'fallback',
                        'objects': ['person', 'background'],
                        'colors': ['blue', 'green', 'white']
                    },
                    'metadata': {'analyzer': 'fallback'}
                }],
                'embeddings': [],
                'metadata': {'status': 'fallback', 'analyzer': 'fallback'}
            }
        else:
            return {
                'segments': [],
                'features': [{
                    'type': 'document_analysis_fallback',
                    'domain': 'text',
                    'confidence': 0.5,
                    'data': {
                        'status': 'fallback',
                        'text_extracted': 'Demo Document für DataFlux'
                    },
                    'metadata': {'analyzer': 'fallback'}
                }],
                'embeddings': [],
                'metadata': {'status': 'fallback', 'analyzer': 'fallback'}
            }
    
    async def _store_analysis_results(self, asset_id, results):
        """Store analysis results in database"""
        try:
            logger.info(f"📊 Storing analysis results for asset {asset_id}")
            logger.info(f">>> Results received: segments={len(results.get('segments', []))}, features={len(results.get('features', []))}, embeddings={len(results.get('embeddings', []))}")
            logger.info(f">>> Features: {results.get('features', [])}")
            
            # Connect to database
            conn = await asyncpg.connect(self.db_url)
            
            try:
                # Store segments
                segments = results.get('segments', [])
                for segment in segments:
                        await conn.execute("""
                            INSERT INTO segments (id, asset_id, segment_type, sequence_number, start_marker, end_marker, confidence_score, duration)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """, 
                        str(uuid.uuid4()),
                        asset_id,
                        segment.get('type', 'unknown'),
                        segment.get('sequence_number', 0),
                        json.dumps(segment.get('start_marker', {})),
                        json.dumps(segment.get('end_marker', {})),
                        segment.get('confidence', 0.0),
                        max(segment.get('duration', 0.0), 1.0)
                        )
                
                # Store features (directly to asset for images, to segments for videos)
                features = results.get('features', [])
                
                for feature in features:
                    # For images: store directly to asset (segment_id = NULL)
                    # For videos: store to segment if available
                    segment_id = None
                    if segments:
                        # Get the first segment for this feature
                        segment_id = await conn.fetchval("""
                            SELECT id FROM segments WHERE asset_id = $1 ORDER BY sequence_number ASC LIMIT 1
                        """, asset_id)
                    
                    await conn.execute("""
                        INSERT INTO features (id, asset_id, segment_id, feature_domain, feature_type, feature_data, confidence, analyzer_version, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """,
                    str(uuid.uuid4()),
                    asset_id,
                    segment_id,  # NULL for images, segment_id for videos
                    feature.get('domain', 'unknown'),
                    feature.get('type', 'unknown'),
                    json.dumps(feature.get('data', {})),
                    feature.get('confidence', 0.0),
                    feature.get('metadata', {}).get('analyzer', 'unknown')
                    )
                
                # Store embeddings
                embeddings = results.get('embeddings', [])
                for embedding in embeddings:
                    await conn.execute("""
                        INSERT INTO embeddings (id, entity_id, embedding_type, model_name, dimensions, vector_id, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """,
                    str(uuid.uuid4()),
                    asset_id,  # entity_id points to asset
                    embedding.get('type', 'unknown'),
                    embedding.get('model', 'unknown'),
                    embedding.get('dimensions', 0),
                    str(uuid.uuid4())  # vector_id for Weaviate reference
                    )
                
                logger.info(f"📊 Stored: {len(segments)} segments, {len(features)} features, {len(embeddings)} embeddings")
                
            finally:
                await conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store analysis results: {e}")
    
    def process_all_assets(self):
        """Verarbeite alle queued assets"""
        logger.info("🔍 Checking for queued assets...")
        
        queued_assets = self.get_queued_assets()
        
        if not queued_assets:
            logger.info("📝 No queued assets found")
            return
        
        logger.info(f"📁 Found {len(queued_assets)} queued assets")
        
        for asset in queued_assets:
            try:
                self.simulate_processing(asset)
            except Exception as e:
                logger.error(f"❌ Failed to process {asset['id']}: {e}")
                self.update_asset_status(asset['id'], 'failed')
                break
    
    def run(self):
        """Run the processor"""
        logger.info("🚀 Starting API Asset Processor")
        
        self.running = True
        
        try:
            while self.running:
                self.process_all_assets()
                logger.info("😴 Waiting 15 seconds before next check...")
                time.sleep(15)
                
        except KeyboardInterrupt:
            logger.info("⏹️  Stopped by user")
        except Exception as e:
            logger.error(f"💥 Processor failed: {e}")
        finally:
            self.running = False
            logger.info("👋 Asset processor stopped")

def main():
    """Main entry point"""
    processor = APIAssetProcessor()
    processor.run()

if __name__ == "__main__":
    main()
