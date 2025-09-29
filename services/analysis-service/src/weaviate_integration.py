"""
DataFlux Analysis Service - Weaviate Integration
Handles vector storage and similarity search for analyzed content
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from weaviate_client import WeaviateClient, WeaviateConfig, create_asset_embedding, create_segment_embedding, create_feature_embedding

logger = logging.getLogger(__name__)

class WeaviateIntegration:
    """Integration with Weaviate vector database"""
    
    def __init__(self, weaviate_url: str = "http://localhost:2005"):
        self.config = WeaviateConfig(url=weaviate_url)
        self.client = WeaviateClient(self.config)
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to Weaviate"""
        try:
            if self.client.health_check():
                self.is_connected = True
                logger.info("✅ Connected to Weaviate")
                return True
            else:
                logger.warning("⚠️ Weaviate not available")
                self.is_connected = False
                return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to Weaviate: {e}")
            self.is_connected = False
            return False
    
    async def store_asset_analysis(self, asset_data: Dict[str, Any], 
                                  embeddings: Dict[str, List[float]]) -> Optional[str]:
        """Store asset analysis results in Weaviate"""
        if not self.is_connected:
            logger.warning("⚠️ Weaviate not connected, skipping asset storage")
            return None
        
        try:
            # Prepare asset data for Weaviate
            weaviate_asset = {
                "entity_id": asset_data.get("entity_id"),
                "filename": asset_data.get("filename"),
                "mime_type": asset_data.get("mime_type"),
                "file_size": asset_data.get("file_size", 0),
                "processing_status": asset_data.get("processing_status", "completed"),
                "created_at": asset_data.get("created_at"),
                "metadata": json.dumps(asset_data.get("metadata", {})),
                "tags": asset_data.get("tags", []),
                "collection_id": asset_data.get("collection_id", "default")
            }
            
            # Use the primary embedding (visual or audio)
            primary_embedding = None
            if "visual_embedding" in embeddings:
                primary_embedding = embeddings["visual_embedding"]
            elif "audio_embedding" in embeddings:
                primary_embedding = embeddings["audio_embedding"]
            elif "text_embedding" in embeddings:
                primary_embedding = embeddings["text_embedding"]
            
            # Create asset in Weaviate
            asset_id = create_asset_embedding(self.client, weaviate_asset, primary_embedding)
            
            if asset_id:
                logger.info(f"✅ Stored asset {asset_data.get('entity_id')} in Weaviate")
                
                # Store additional embeddings as features
                await self._store_additional_embeddings(asset_id, embeddings)
                
                return asset_id
            else:
                logger.error(f"❌ Failed to store asset {asset_data.get('entity_id')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error storing asset analysis: {e}")
            return None
    
    async def store_segment_analysis(self, segment_data: Dict[str, Any],
                                   embeddings: Dict[str, List[float]]) -> Optional[str]:
        """Store segment analysis results in Weaviate"""
        if not self.is_connected:
            logger.warning("⚠️ Weaviate not connected, skipping segment storage")
            return None
        
        try:
            # Prepare segment data for Weaviate
            weaviate_segment = {
                "segment_id": segment_data.get("segment_id"),
                "asset_id": segment_data.get("asset_id"),
                "segment_type": segment_data.get("segment_type"),
                "sequence_number": segment_data.get("sequence_number", 0),
                "start_time": segment_data.get("start_time", 0.0),
                "end_time": segment_data.get("end_time", 0.0),
                "confidence_score": segment_data.get("confidence_score", 0.0),
                "content_description": segment_data.get("content_description", ""),
                "detected_objects": segment_data.get("detected_objects", []),
                "detected_text": segment_data.get("detected_text", ""),
                "audio_features": json.dumps(segment_data.get("audio_features", {})),
                "visual_features": json.dumps(segment_data.get("visual_features", {}))
            }
            
            # Use the primary embedding
            primary_embedding = None
            if "visual_embedding" in embeddings:
                primary_embedding = embeddings["visual_embedding"]
            elif "audio_embedding" in embeddings:
                primary_embedding = embeddings["audio_embedding"]
            elif "text_embedding" in embeddings:
                primary_embedding = embeddings["text_embedding"]
            
            # Create segment in Weaviate
            segment_id = create_segment_embedding(self.client, weaviate_segment, primary_embedding)
            
            if segment_id:
                logger.info(f"✅ Stored segment {segment_data.get('segment_id')} in Weaviate")
                return segment_id
            else:
                logger.error(f"❌ Failed to store segment {segment_data.get('segment_id')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error storing segment analysis: {e}")
            return None
    
    async def _store_additional_embeddings(self, asset_id: str, 
                                         embeddings: Dict[str, List[float]]):
        """Store additional embeddings as features"""
        try:
            for embedding_type, embedding_vector in embeddings.items():
                if embedding_type == "primary_embedding":
                    continue  # Skip primary embedding as it's already stored
                
                feature_data = {
                    "feature_id": f"{asset_id}_{embedding_type}",
                    "entity_id": asset_id,
                    "feature_type": embedding_type.split("_")[0],  # visual, audio, text
                    "feature_domain": "embedding",
                    "feature_name": embedding_type,
                    "confidence_score": 1.0,
                    "feature_data": json.dumps({"dimensions": len(embedding_vector)}),
                    "embedding_model": "dataflux_analyzer",
                    "embedding_dimensions": len(embedding_vector),
                    "created_at": "2025-09-28T20:00:00Z"
                }
                
                create_feature_embedding(self.client, feature_data, embedding_vector)
                
        except Exception as e:
            logger.error(f"❌ Error storing additional embeddings: {e}")
    
    async def search_similar_content(self, query_vector: List[float], 
                                   content_type: str = "asset",
                                   limit: int = 10,
                                   collection_id: str = None) -> List[Dict[str, Any]]:
        """Search for similar content using vector similarity"""
        if not self.is_connected:
            logger.warning("⚠️ Weaviate not connected, returning empty results")
            return []
        
        try:
            if content_type == "asset":
                return self.client.search_objects(
                    "Asset",
                    vector=query_vector,
                    limit=limit,
                    where_filter={
                        "path": ["collection_id"],
                        "operator": "Equal",
                        "valueString": collection_id
                    } if collection_id else None
                )
            elif content_type == "segment":
                return self.client.search_objects(
                    "Segment",
                    vector=query_vector,
                    limit=limit
                )
            else:
                logger.warning(f"⚠️ Unknown content type: {content_type}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error searching similar content: {e}")
            return []
    
    async def hybrid_search(self, query_text: str, query_vector: List[float],
                          content_type: str = "asset", limit: int = 10) -> List[Dict[str, Any]]:
        """Perform hybrid search (text + vector)"""
        if not self.is_connected:
            logger.warning("⚠️ Weaviate not connected, returning empty results")
            return []
        
        try:
            if content_type == "asset":
                return self.client.search_objects(
                    "Asset",
                    query=query_text,
                    vector=query_vector,
                    limit=limit,
                    hybrid=True
                )
            elif content_type == "segment":
                return self.client.search_objects(
                    "Segment",
                    query=query_text,
                    vector=query_vector,
                    limit=limit,
                    hybrid=True
                )
            else:
                logger.warning(f"⚠️ Unknown content type: {content_type}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error performing hybrid search: {e}")
            return []
    
    async def get_asset_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset by Weaviate object ID"""
        if not self.is_connected:
            return None
        
        try:
            return self.client.get_object(asset_id)
        except Exception as e:
            logger.error(f"❌ Error getting asset: {e}")
            return None
    
    async def update_asset_metadata(self, asset_id: str, metadata: Dict[str, Any]) -> bool:
        """Update asset metadata in Weaviate"""
        if not self.is_connected:
            return False
        
        try:
            return self.client.update_object(asset_id, {"metadata": json.dumps(metadata)})
        except Exception as e:
            logger.error(f"❌ Error updating asset metadata: {e}")
            return False
    
    async def delete_asset(self, asset_id: str) -> bool:
        """Delete asset from Weaviate"""
        if not self.is_connected:
            return False
        
        try:
            return self.client.delete_object(asset_id)
        except Exception as e:
            logger.error(f"❌ Error deleting asset: {e}")
            return False

# Mock implementation for testing without Weaviate
class MockWeaviateIntegration:
    """Mock Weaviate integration for testing"""
    
    def __init__(self, weaviate_url: str = "http://localhost:2005"):
        self.is_connected = False
        self.stored_assets = {}
        self.stored_segments = {}
        
    async def connect(self) -> bool:
        """Mock connection"""
        self.is_connected = True
        logger.info("✅ Mock Weaviate connected")
        return True
    
    async def store_asset_analysis(self, asset_data: Dict[str, Any], 
                                  embeddings: Dict[str, List[float]]) -> Optional[str]:
        """Mock asset storage"""
        asset_id = f"mock_{asset_data.get('entity_id')}"
        self.stored_assets[asset_id] = {
            "asset_data": asset_data,
            "embeddings": embeddings
        }
        logger.info(f"✅ Mock stored asset {asset_data.get('entity_id')}")
        return asset_id
    
    async def store_segment_analysis(self, segment_data: Dict[str, Any],
                                   embeddings: Dict[str, List[float]]) -> Optional[str]:
        """Mock segment storage"""
        segment_id = f"mock_{segment_data.get('segment_id')}"
        self.stored_segments[segment_id] = {
            "segment_data": segment_data,
            "embeddings": embeddings
        }
        logger.info(f"✅ Mock stored segment {segment_data.get('segment_id')}")
        return segment_id
    
    async def search_similar_content(self, query_vector: List[float], 
                                   content_type: str = "asset",
                                   limit: int = 10,
                                   collection_id: str = None) -> List[Dict[str, Any]]:
        """Mock similarity search"""
        logger.info(f"✅ Mock similarity search for {content_type}")
        return []
    
    async def hybrid_search(self, query_text: str, query_vector: List[float],
                          content_type: str = "asset", limit: int = 10) -> List[Dict[str, Any]]:
        """Mock hybrid search"""
        logger.info(f"✅ Mock hybrid search: {query_text}")
        return []
    
    async def get_asset_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Mock get asset"""
        return self.stored_assets.get(asset_id)
    
    async def update_asset_metadata(self, asset_id: str, metadata: Dict[str, Any]) -> bool:
        """Mock update metadata"""
        if asset_id in self.stored_assets:
            self.stored_assets[asset_id]["asset_data"]["metadata"] = metadata
            return True
        return False
    
    async def delete_asset(self, asset_id: str) -> bool:
        """Mock delete asset"""
        if asset_id in self.stored_assets:
            del self.stored_assets[asset_id]
            return True
        return False

# Test function
async def test_weaviate_integration():
    """Test the Weaviate integration"""
    print("🧪 Testing Weaviate Integration")
    print("=" * 40)
    
    # Use mock implementation for testing
    weaviate = MockWeaviateIntegration()
    
    # Test connection
    await weaviate.connect()
    
    # Test asset storage
    asset_data = {
        "entity_id": "test-asset-001",
        "filename": "test_video.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
        "processing_status": "completed",
        "created_at": "2025-09-28T20:00:00Z",
        "metadata": {"duration": 120.5, "resolution": "1920x1080"},
        "tags": ["video", "test"],
        "collection_id": "default"
    }
    
    embeddings = {
        "visual_embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        "audio_embedding": [0.6, 0.7, 0.8, 0.9, 1.0],
        "text_embedding": [0.2, 0.4, 0.6, 0.8, 1.0]
    }
    
    asset_id = await weaviate.store_asset_analysis(asset_data, embeddings)
    print(f"✅ Stored asset with ID: {asset_id}")
    
    # Test segment storage
    segment_data = {
        "segment_id": "test-segment-001",
        "asset_id": "test-asset-001",
        "segment_type": "scene",
        "sequence_number": 1,
        "start_time": 0.0,
        "end_time": 10.0,
        "confidence_score": 0.95,
        "content_description": "Opening scene with car",
        "detected_objects": ["car", "road", "sky"],
        "detected_text": "",
        "audio_features": {},
        "visual_features": {}
    }
    
    segment_id = await weaviate.store_segment_analysis(segment_data, embeddings)
    print(f"✅ Stored segment with ID: {segment_id}")
    
    # Test similarity search
    query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    similar_assets = await weaviate.search_similar_content(query_vector, "asset", 5)
    print(f"✅ Found {len(similar_assets)} similar assets")
    
    # Test hybrid search
    hybrid_results = await weaviate.hybrid_search("car video", query_vector, "asset", 5)
    print(f"✅ Hybrid search returned {len(hybrid_results)} results")
    
    print("\n🎉 Weaviate integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_weaviate_integration())
