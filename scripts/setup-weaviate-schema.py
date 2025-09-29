#!/usr/bin/env python3
"""
DataFlux Weaviate Schema Setup
Creates the vector database schema for embeddings and similarity search
"""

import json
import requests
import time
from typing import Dict, List, Any

class WeaviateSchemaManager:
    def __init__(self, weaviate_url: str = "http://localhost:2005"):
        self.weaviate_url = weaviate_url
        self.client_url = f"{weaviate_url}/v1"
        
    def wait_for_weaviate(self, max_attempts: int = 30) -> bool:
        """Wait for Weaviate to be ready"""
        print("⏳ Waiting for Weaviate to be ready...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.client_url}/meta", timeout=5)
                if response.status_code == 200:
                    print("✅ Weaviate is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print(f"⏳ Attempt {attempt + 1}/{max_attempts}: Weaviate not ready yet...")
            time.sleep(2)
        
        print("❌ Weaviate failed to start after maximum attempts")
        return False
    
    def create_schema(self) -> bool:
        """Create the DataFlux schema in Weaviate"""
        print("🔧 Creating DataFlux schema in Weaviate...")
        
        # Define the schema
        schema = {
            "classes": [
                {
                    "class": "Asset",
                    "description": "Media assets with embeddings",
                    "vectorizer": "none",  # We'll provide our own vectors
                    "properties": [
                        {
                            "name": "entity_id",
                            "dataType": ["string"],
                            "description": "Unique entity identifier",
                            "indexInverted": True
                        },
                        {
                            "name": "filename",
                            "dataType": ["string"],
                            "description": "Original filename",
                            "indexInverted": True
                        },
                        {
                            "name": "mime_type",
                            "dataType": ["string"],
                            "description": "MIME type of the file",
                            "indexInverted": True
                        },
                        {
                            "name": "file_size",
                            "dataType": ["int"],
                            "description": "File size in bytes"
                        },
                        {
                            "name": "processing_status",
                            "dataType": ["string"],
                            "description": "Processing status",
                            "indexInverted": True
                        },
                        {
                            "name": "created_at",
                            "dataType": ["date"],
                            "description": "Creation timestamp"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["object"],
                            "description": "Additional metadata"
                        },
                        {
                            "name": "tags",
                            "dataType": ["string[]"],
                            "description": "Content tags",
                            "indexInverted": True
                        },
                        {
                            "name": "collection_id",
                            "dataType": ["string"],
                            "description": "Collection identifier",
                            "indexInverted": True
                        }
                    ]
                },
                {
                    "class": "Segment",
                    "description": "Media segments (scenes, frames, audio clips)",
                    "vectorizer": "none",
                    "properties": [
                        {
                            "name": "segment_id",
                            "dataType": ["string"],
                            "description": "Unique segment identifier",
                            "indexInverted": True
                        },
                        {
                            "name": "asset_id",
                            "dataType": ["string"],
                            "description": "Parent asset identifier",
                            "indexInverted": True
                        },
                        {
                            "name": "segment_type",
                            "dataType": ["string"],
                            "description": "Type of segment (scene, frame, clip)",
                            "indexInverted": True
                        },
                        {
                            "name": "sequence_number",
                            "dataType": ["int"],
                            "description": "Sequence number in parent asset"
                        },
                        {
                            "name": "start_time",
                            "dataType": ["number"],
                            "description": "Start time in seconds"
                        },
                        {
                            "name": "end_time",
                            "dataType": ["number"],
                            "description": "End time in seconds"
                        },
                        {
                            "name": "confidence_score",
                            "dataType": ["number"],
                            "description": "Confidence score for this segment"
                        },
                        {
                            "name": "content_description",
                            "dataType": ["text"],
                            "description": "Description of segment content",
                            "indexInverted": True
                        },
                        {
                            "name": "detected_objects",
                            "dataType": ["string[]"],
                            "description": "Detected objects in segment",
                            "indexInverted": True
                        },
                        {
                            "name": "detected_text",
                            "dataType": ["text"],
                            "description": "OCR detected text",
                            "indexInverted": True
                        },
                        {
                            "name": "audio_features",
                            "dataType": ["object"],
                            "description": "Audio feature data"
                        },
                        {
                            "name": "visual_features",
                            "dataType": ["object"],
                            "description": "Visual feature data"
                        }
                    ]
                },
                {
                    "class": "Feature",
                    "description": "Extracted features and embeddings",
                    "vectorizer": "none",
                    "properties": [
                        {
                            "name": "feature_id",
                            "dataType": ["string"],
                            "description": "Unique feature identifier",
                            "indexInverted": True
                        },
                        {
                            "name": "entity_id",
                            "dataType": ["string"],
                            "description": "Entity this feature belongs to",
                            "indexInverted": True
                        },
                        {
                            "name": "feature_type",
                            "dataType": ["string"],
                            "description": "Type of feature (visual, audio, text)",
                            "indexInverted": True
                        },
                        {
                            "name": "feature_domain",
                            "dataType": ["string"],
                            "description": "Domain of the feature",
                            "indexInverted": True
                        },
                        {
                            "name": "feature_name",
                            "dataType": ["string"],
                            "description": "Name of the specific feature",
                            "indexInverted": True
                        },
                        {
                            "name": "confidence_score",
                            "dataType": ["number"],
                            "description": "Confidence score for this feature"
                        },
                        {
                            "name": "feature_data",
                            "dataType": ["object"],
                            "description": "Raw feature data"
                        },
                        {
                            "name": "embedding_model",
                            "dataType": ["string"],
                            "description": "Model used for embedding",
                            "indexInverted": True
                        },
                        {
                            "name": "embedding_dimensions",
                            "dataType": ["int"],
                            "description": "Dimensions of the embedding vector"
                        },
                        {
                            "name": "created_at",
                            "dataType": ["date"],
                            "description": "Feature extraction timestamp"
                        }
                    ]
                }
            ]
        }
        
        try:
            # Create schema
            response = requests.post(
                f"{self.client_url}/schema",
                json=schema,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Schema created successfully!")
                return True
            else:
                print(f"❌ Failed to create schema: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating schema: {e}")
            return False
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the current schema"""
        try:
            response = requests.get(f"{self.client_url}/schema", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get schema: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting schema: {e}")
            return {}
    
    def delete_schema(self) -> bool:
        """Delete the entire schema (for testing)"""
        print("🗑️ Deleting existing schema...")
        
        try:
            schema = self.get_schema()
            if not schema or 'classes' not in schema:
                print("ℹ️ No schema to delete")
                return True
            
            for class_info in schema['classes']:
                class_name = class_info['class']
                response = requests.delete(f"{self.client_url}/schema/{class_name}", timeout=10)
                if response.status_code == 200:
                    print(f"✅ Deleted class: {class_name}")
                else:
                    print(f"❌ Failed to delete class {class_name}: {response.status_code}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error deleting schema: {e}")
            return False
    
    def test_schema(self) -> bool:
        """Test the schema by adding a sample object"""
        print("🧪 Testing schema with sample data...")
        
        sample_asset = {
            "entity_id": "test-asset-001",
            "filename": "sample_video.mp4",
            "mime_type": "video/mp4",
            "file_size": 1024000,
            "processing_status": "completed",
            "created_at": "2025-09-28T20:00:00Z",
            "metadata": {
                "duration": 120.5,
                "resolution": "1920x1080",
                "fps": 30
            },
            "tags": ["video", "sample", "test"],
            "collection_id": "default"
        }
        
        try:
            response = requests.post(
                f"{self.client_url}/objects",
                json=sample_asset,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Sample asset created successfully!")
                return True
            else:
                print(f"❌ Failed to create sample asset: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating sample asset: {e}")
            return False

def main():
    """Main function to set up Weaviate schema"""
    print("🚀 DataFlux Weaviate Schema Setup")
    print("=" * 50)
    
    manager = WeaviateSchemaManager()
    
    # Wait for Weaviate to be ready
    if not manager.wait_for_weaviate():
        print("❌ Cannot proceed without Weaviate")
        return False
    
    # Delete existing schema (for clean setup)
    manager.delete_schema()
    
    # Create new schema
    if not manager.create_schema():
        print("❌ Failed to create schema")
        return False
    
    # Test the schema
    if not manager.test_schema():
        print("❌ Schema test failed")
        return False
    
    print("\n🎉 Weaviate schema setup completed successfully!")
    print("📊 Schema classes created:")
    print("  - Asset: Media assets with embeddings")
    print("  - Segment: Media segments (scenes, frames, clips)")
    print("  - Feature: Extracted features and embeddings")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
