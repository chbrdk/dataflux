#!/usr/bin/env python3
"""
Working Asset Processor - Simplest possible implementation
"""

import asyncio
import json
import logging
import os
import sqlite3
import uuid
import time
from datetime import datetime
from typing import Dict, List

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkingAssetProcessor:
    """Working asset processor"""
    
    def __init__(self):
        self.db_file = "dataflux.db"
        self.running = False
        
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                status TEXT DEFAULT 'queued',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS segments (
                id TEXT PRIMARY KEY,
                asset_id TEXT,
                segment_type TEXT,
                start_marker REAL,
                end_marker REAL,
                confidence_score REAL,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS features (
                id TEXT PRIMARY KEY,
                segment_id TEXT,
                feature_type TEXT,
                feature_domain TEXT,
                confidence_score REAL,
                feature_data TEXT,
                metadata TEXT
            )
        ''')
        
        # Insert test data if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO assets (id, filename, file_size, mime_type, status)
            VALUES ('test1', 'test_video.mp4', 19, 'video/mp4', 'queued')
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO assets (id, filename, file_size, mime_type, status)
            VALUES ('test2', 'Cheesy Dad Basket.mp4', 48411030, 'video/mp4', 'queued')
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def get_queued_assets(self) -> List[Dict]:
        """Get queued assets"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM assets WHERE status = 'queued' 
            ORDER BY created_at ASC LIMIT 5
        ''')
        
        assets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return assets
    
    def update_asset_status(self, asset_id: str, status: str):
        """Update asset status"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE assets SET status = ? WHERE id = ?
        ''', (status, asset_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated asset {asset_id} to {status}")
    
    def generate_analysis_data(self, asset_id: str, mime_type: str):
        """Generate analysis data"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Insert segment
        segment_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO segments (
                id, asset_id, segment_type, start_marker, end_marker,
                confidence_score, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            segment_id, asset_id, 'processed_segment', 0, 10.0, 0.95,
            json.dumps({
                'media_type': mime_type,
                'processed_at': datetime.utcnow().isoformat(),
                'analysis_version': '1.0'
            })
        ))
        
        # Insert feature
        feature_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO features (
                id, segment_id, feature_type, feature_domain,
                confidence_score, feature_data, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            feature_id, segment_id, 'analysis_complete', 'processing',
            1.0, json.dumps({'status': 'completed'}),
            json.dumps({'asset_id': asset_id})
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Generated analysis data for {asset_id}")
    
    def process_asset(self, asset: Dict):
        """Process a single asset"""
        asset_id = asset['id']
        filename = asset['filename']
        mime_type = asset['mime_type']
        
        logger.info(f"🔄 Processing {filename} ({mime_type})")
        
        # Update to processing
        self.update_asset_status(asset_id, 'processing')
        
        # Simulate processing based on file type
        if mime_type.startswith('video/'):
            processing_time = 8
        elif mime_type.startswith('image/'):
            processing_time = 1
        elif mime_type.startswith('audio/'):
            processing_time = 3
        else:
            processing_time = 2
        
        logger.info(f"⏱️  Simulating {processing_time}s processing...")
        time.sleep(min(processing_time, 5))  # Max 5 seconds for demo
        
        # Generate analysis data
        self.generate_analysis_data(asset_id, mime_type)
        
        # Mark as completed
        self.update_asset_status(asset_id, 'completed')
        logger.info(f"✅ Completed processing {filename}")
    
    def process_all_assets(self):
        """Process all queued assets"""
        logger.info("🔍 Checking for queued assets...")
        
        queued_assets = self.get_queued_assets()
        
        if not queued_assets:
            logger.info("📝 No queued assets found")
            return
        
        logger.info(f"📁 Found {len(queued_assets)} queued assets")
        
        for asset in queued_assets:
            try:
                self.process_asset(asset)
            except Exception as e:
                logger.error(f"❌ Failed to process {asset['id']}: {e}")
                self.update_asset_status(asset['id'], 'failed')
                break  # Stop on error
    
    def run(self):
        """Run the processor"""
        logger.info("🚀 Starting Working Asset Processor")
        
        # Initialize database
        self.init_database()
        
        self.running = True
        
        try:
            while self.running:
                self.process_all_assets()
                logger.info("😴 Waiting 10 seconds before next check...")
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("⏹️  Stopped by user")
        except Exception as e:
            logger.error(f"💥 Processor failed: {e}")
        finally:
            self.running = False
            logger.info("👋 Asset processor stopped")

def main():
    """Main entry point"""
    processor = WorkingAssetProcessor()
    processor.run()

if __name__ == "__main__":
    main()
