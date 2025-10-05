#!/usr/bin/env python3
"""
Test script for Face Database functionality
"""

import sys
import os
sys.path.append('/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service')

from analyzers.facenet_analyzer import FaceNetAnalyzer
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_face_database():
    """Test the face database functionality"""
    logger.info("🧪 Starting Face Database Test")
    
    # Initialize analyzer
    analyzer = FaceNetAnalyzer()
    
    # Check if database file exists
    db_file = "/tmp/dataflux_face_database.json"
    logger.info(f"📁 Database file: {db_file}")
    logger.info(f"📁 File exists: {os.path.exists(db_file)}")
    
    # Check face database state
    logger.info(f"📊 Face database size: {len(analyzer.face_database)}")
    logger.info(f"📊 Face embeddings size: {len(analyzer.face_embeddings)}")
    
    # List faces in database
    if analyzer.face_database:
        logger.info("👥 Faces in database:")
        for face_id, face_info in analyzer.face_database.items():
            logger.info(f"  - {face_id}: {face_info.get('identity', 'Unknown')}")
    else:
        logger.info("📭 No faces in database")
    
    # Test with a sample image if available
    test_image = "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/_CHB8104.jpg"
    if os.path.exists(test_image):
        logger.info(f"🖼️ Testing with image: {test_image}")
        try:
            result = await analyzer.analyze(test_image, {})
            logger.info(f"✅ Analysis completed: {len(result.get('features', []))} features")
            
            # Check face recognition features
            face_features = [f for f in result.get('features', []) if f.get('type') == 'face_recognition']
            if face_features:
                logger.info(f"🧑 Face recognition features: {len(face_features)}")
                for feature in face_features:
                    faces = feature.get('data', {}).get('recognized_faces', [])
                    for face in faces:
                        logger.info(f"  - Face ID: {face.get('face_id')}")
                        logger.info(f"  - Identity: {face.get('identity')}")
                        logger.info(f"  - Known: {face.get('is_known_face')}")
                        logger.info(f"  - Confidence: {face.get('confidence')}")
            else:
                logger.info("❌ No face recognition features found")
                
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
    else:
        logger.info(f"❌ Test image not found: {test_image}")
    
    # Check database after analysis
    logger.info(f"📊 Face database size after analysis: {len(analyzer.face_database)}")
    logger.info(f"📊 Face embeddings size after analysis: {len(analyzer.face_embeddings)}")
    
    # Check if database file was created
    logger.info(f"📁 Database file exists after analysis: {os.path.exists(db_file)}")
    if os.path.exists(db_file):
        with open(db_file, 'r') as f:
            import json
            data = json.load(f)
            logger.info(f"📄 Database file content: {len(data.get('face_database', {}))} faces")

if __name__ == "__main__":
    asyncio.run(test_face_database())
