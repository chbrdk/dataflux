#!/usr/bin/env python3
"""
API-based Asset Processor - kommuniziert direkt mit Ingestion Service
"""

import requests
import json
import time
import logging
import uuid
from datetime import datetime

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
        
        # Simuliere Analyse-Ergebnisse
        self.generate_analysis_results(asset)
        
        # Mark as completed
        self.update_asset_status(asset_id, 'completed')
        logger.info(f"✅ Completed processing {filename}")
    
    def generate_analysis_results(self, asset):
        """Generiere Analyse-Ergebnisse"""
        asset_id = asset['id']
        filename = asset['filename']
        mime_type = asset['mime_type']
        
        # Simuliere verschiedene Analyse-Ergebnisse je nach Dateityp
        if mime_type.startswith('video/'):
            results = {
                'video_analysis': 'completed',
                'object_detection': ['person', 'building', 'car'],
                'audio_segments': ['speech', 'music', 'silence'],
                'transcript': 'Demo Video mit verschiedenen Inhalten'
            }
        elif mime_type.startswith('image/'):
            results = {
                'image_analysis': 'completed',
                'objects': ['person', 'background'],
                'colors': ['blue', 'green', 'white'],
                'text_recognition': 'DataFlux Demo Image'
            }
        elif mime_type.startswith('audio/'):
            results = {
                'audio_analysis': 'completed',
                'speech_recognized': 'Demo Audio für DataFlux',
                'music_features': ['tempo: 120', 'key: C major'],
                'audio_segments': ['intro', 'main', 'outro']
            }
        else:
            results = {
                'document_analysis': 'completed',
                'text_extracted': 'Dies ist ein Demo-Dokument für DataFlux',
                'metadata': {'pages': 1, 'language': 'de'}
            }
        
        logger.info(f"🧠 Generated analysis for {filename}: {json.dumps(results, ensure_ascii=False, indent=2)}")
        
        return results
    
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
