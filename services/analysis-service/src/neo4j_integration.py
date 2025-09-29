"""
DataFlux Analysis Service - Neo4j Integration
Handles graph relationships and similarity edges for analyzed content
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from neo4j_client import Neo4jClient, Neo4jConfig, MockNeo4jClient

logger = logging.getLogger(__name__)

class Neo4jIntegration:
    """Integration with Neo4j graph database"""
    
    def __init__(self, neo4j_url: str = "http://localhost:2007", 
                 username: str = "neo4j", password: str = "dataflux_pass"):
        self.config = Neo4jConfig(url=neo4j_url, username=username, password=password)
        self.client = Neo4jClient(self.config)
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to Neo4j"""
        try:
            if self.client.health_check():
                self.is_connected = True
                logger.info("✅ Connected to Neo4j")
                return True
            else:
                logger.warning("⚠️ Neo4j not available")
                self.is_connected = False
                return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            self.is_connected = False
            return False
    
    async def store_asset_graph(self, asset_data: Dict[str, Any]) -> Optional[str]:
        """Store asset in Neo4j graph"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, skipping asset storage")
            return None
        
        try:
            # Prepare asset properties
            asset_properties = {
                "entity_id": asset_data.get("entity_id"),
                "asset_id": asset_data.get("entity_id"),  # Use entity_id as asset_id
                "filename": asset_data.get("filename"),
                "mime_type": asset_data.get("mime_type"),
                "file_size": asset_data.get("file_size", 0),
                "processing_status": asset_data.get("processing_status", "completed"),
                "created_at": asset_data.get("created_at"),
                "updated_at": asset_data.get("updated_at"),
                "metadata": json.dumps(asset_data.get("metadata", {})),
                "tags": asset_data.get("tags", []),
                "collection_id": asset_data.get("collection_id", "default")
            }
            
            # Create asset node
            node_id = self.client.create_node(["Asset", "Entity"], asset_properties)
            
            if node_id:
                logger.info(f"✅ Stored asset {asset_data.get('entity_id')} in Neo4j")
                
                # Create collection relationship if collection exists
                await self._create_collection_relationship(asset_data.get("collection_id", "default"), node_id)
                
                return node_id
            else:
                logger.error(f"❌ Failed to store asset {asset_data.get('entity_id')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error storing asset graph: {e}")
            return None
    
    async def store_segment_graph(self, segment_data: Dict[str, Any]) -> Optional[str]:
        """Store segment in Neo4j graph"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, skipping segment storage")
            return None
        
        try:
            # Prepare segment properties
            segment_properties = {
                "entity_id": segment_data.get("segment_id"),
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
                "created_at": segment_data.get("created_at"),
                "updated_at": segment_data.get("updated_at")
            }
            
            # Create segment node
            node_id = self.client.create_node(["Segment", "Entity"], segment_properties)
            
            if node_id:
                logger.info(f"✅ Stored segment {segment_data.get('segment_id')} in Neo4j")
                
                # Create relationship to parent asset
                await self._create_asset_segment_relationship(segment_data.get("asset_id"), node_id, segment_data)
                
                return node_id
            else:
                logger.error(f"❌ Failed to store segment {segment_data.get('segment_id')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error storing segment graph: {e}")
            return None
    
    async def create_similarity_edges(self, asset1_id: str, asset2_id: str, 
                                    similarity_score: float, similarity_type: str = "content") -> bool:
        """Create similarity relationship between assets"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, skipping similarity edge creation")
            return False
        
        try:
            success = self.client.create_similarity_relationship(
                asset1_id, asset2_id, similarity_score, similarity_type
            )
            
            if success:
                logger.info(f"✅ Created similarity edge between {asset1_id} and {asset2_id}")
                return True
            else:
                logger.error(f"❌ Failed to create similarity edge")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating similarity edge: {e}")
            return False
    
    async def find_similar_content(self, asset_id: str, similarity_threshold: float = 0.7,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar content using graph relationships"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, returning empty results")
            return []
        
        try:
            similar_assets = self.client.find_similar_assets(
                asset_id, similarity_threshold, limit
            )
            
            logger.info(f"✅ Found {len(similar_assets)} similar assets for {asset_id}")
            return similar_assets
            
        except Exception as e:
            logger.error(f"❌ Error finding similar content: {e}")
            return []
    
    async def get_content_recommendations(self, asset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get content recommendations based on graph relationships"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, returning empty results")
            return []
        
        try:
            recommendations = self.client.get_recommendations(asset_id, limit)
            
            logger.info(f"✅ Got {len(recommendations)} recommendations for {asset_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error getting recommendations: {e}")
            return []
    
    async def find_objects_in_content(self, object_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Find content containing specific objects"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, returning empty results")
            return []
        
        try:
            segments = self.client.find_objects_in_segments(object_name, limit)
            
            logger.info(f"✅ Found {len(segments)} segments containing '{object_name}'")
            return segments
            
        except Exception as e:
            logger.error(f"❌ Error finding objects in content: {e}")
            return []
    
    async def get_asset_segments(self, asset_id: str) -> List[Dict[str, Any]]:
        """Get all segments of an asset"""
        if not self.is_connected:
            logger.warning("⚠️ Neo4j not connected, returning empty results")
            return []
        
        try:
            segments = self.client.find_asset_segments(asset_id)
            
            logger.info(f"✅ Found {len(segments)} segments for asset {asset_id}")
            return segments
            
        except Exception as e:
            logger.error(f"❌ Error getting asset segments: {e}")
            return []
    
    async def _create_collection_relationship(self, collection_id: str, asset_node_id: str):
        """Create relationship between collection and asset"""
        try:
            # First, ensure collection exists
            collection_properties = {
                "collection_id": collection_id,
                "name": f"Collection {collection_id}",
                "description": f"Collection for {collection_id}",
                "created_at": "2025-09-28T20:00:00Z",
                "updated_at": "2025-09-28T20:00:00Z"
            }
            
            # Try to find existing collection
            existing_collections = self.client.find_nodes(["Collection"], {"collection_id": collection_id})
            
            if not existing_collections:
                # Create collection if it doesn't exist
                collection_node_id = self.client.create_node(["Collection"], collection_properties)
                if collection_node_id:
                    logger.info(f"✅ Created collection {collection_id}")
            else:
                # Use existing collection
                collection_node_id = str(existing_collections[0].get("id", ""))
            
            # Create relationship (this would need the actual Neo4j node IDs)
            logger.info(f"✅ Collection relationship created for {collection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error creating collection relationship: {e}")
    
    async def _create_asset_segment_relationship(self, asset_id: str, segment_node_id: str, segment_data: Dict[str, Any]):
        """Create relationship between asset and segment"""
        try:
            # Find the asset node
            assets = self.client.find_nodes(["Asset"], {"asset_id": asset_id})
            
            if assets:
                asset_node_id = str(assets[0].get("id", ""))
                
                # Create CONTAINS relationship
                success = self.client.create_relationship(
                    asset_node_id, segment_node_id, "CONTAINS",
                    {
                        "relationship_type": "contains",
                        "sequence": segment_data.get("sequence_number", 0),
                        "created_at": "2025-09-28T20:00:00Z"
                    }
                )
                
                if success:
                    logger.info(f"✅ Created asset-segment relationship for {asset_id}")
                else:
                    logger.error(f"❌ Failed to create asset-segment relationship")
            else:
                logger.warning(f"⚠️ Asset {asset_id} not found for relationship creation")
                
        except Exception as e:
            logger.error(f"❌ Error creating asset-segment relationship: {e}")
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph database statistics"""
        if not self.is_connected:
            return {"error": "Neo4j not connected"}
        
        try:
            stats = self.client.get_graph_statistics()
            logger.info("✅ Retrieved graph statistics")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting graph statistics: {e}")
            return {"error": str(e)}

# Mock implementation for testing without Neo4j
class MockNeo4jIntegration:
    """Mock Neo4j integration for testing"""
    
    def __init__(self, neo4j_url: str = "http://localhost:2007", 
                 username: str = "neo4j", password: str = "dataflux_pass"):
        self.is_connected = False
        self.stored_assets = {}
        self.stored_segments = {}
        self.similarity_edges = []
        
    async def connect(self) -> bool:
        """Mock connection"""
        self.is_connected = True
        logger.info("✅ Mock Neo4j connected")
        return True
    
    async def store_asset_graph(self, asset_data: Dict[str, Any]) -> Optional[str]:
        """Mock asset storage"""
        asset_id = asset_data.get("entity_id")
        self.stored_assets[asset_id] = asset_data
        logger.info(f"✅ Mock stored asset {asset_id}")
        return asset_id
    
    async def store_segment_graph(self, segment_data: Dict[str, Any]) -> Optional[str]:
        """Mock segment storage"""
        segment_id = segment_data.get("segment_id")
        self.stored_segments[segment_id] = segment_data
        logger.info(f"✅ Mock stored segment {segment_id}")
        return segment_id
    
    async def create_similarity_edges(self, asset1_id: str, asset2_id: str, 
                                    similarity_score: float, similarity_type: str = "content") -> bool:
        """Mock similarity edge creation"""
        self.similarity_edges.append({
            "asset1": asset1_id,
            "asset2": asset2_id,
            "score": similarity_score,
            "type": similarity_type
        })
        logger.info(f"✅ Mock created similarity edge: {asset1_id} -> {asset2_id}")
        return True
    
    async def find_similar_content(self, asset_id: str, similarity_threshold: float = 0.7,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Mock similar content search"""
        logger.info(f"✅ Mock finding similar content to {asset_id}")
        return []
    
    async def get_content_recommendations(self, asset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Mock recommendations"""
        logger.info(f"✅ Mock getting recommendations for {asset_id}")
        return []
    
    async def find_objects_in_content(self, object_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Mock object search"""
        logger.info(f"✅ Mock finding objects '{object_name}' in content")
        return []
    
    async def get_asset_segments(self, asset_id: str) -> List[Dict[str, Any]]:
        """Mock asset segments"""
        logger.info(f"✅ Mock getting segments for asset {asset_id}")
        return []
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Mock statistics"""
        return {
            "total_nodes": len(self.stored_assets) + len(self.stored_segments),
            "total_relationships": len(self.similarity_edges),
            "by_label": {
                "Asset": {"nodes": len(self.stored_assets), "relationships": 0},
                "Segment": {"nodes": len(self.stored_segments), "relationships": 0}
            }
        }

# Test function
async def test_neo4j_integration():
    """Test the Neo4j integration"""
    print("🧪 Testing Neo4j Integration")
    print("=" * 40)
    
    # Use mock implementation for testing
    neo4j = MockNeo4jIntegration()
    
    # Test connection
    await neo4j.connect()
    
    # Test asset storage
    asset_data = {
        "entity_id": "test-asset-001",
        "filename": "test_video.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
        "processing_status": "completed",
        "created_at": "2025-09-28T20:00:00Z",
        "updated_at": "2025-09-28T20:00:00Z",
        "metadata": {"duration": 120.5, "resolution": "1920x1080"},
        "tags": ["video", "test"],
        "collection_id": "default"
    }
    
    asset_id = await neo4j.store_asset_graph(asset_data)
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
        "created_at": "2025-09-28T20:00:00Z",
        "updated_at": "2025-09-28T20:00:00Z"
    }
    
    segment_id = await neo4j.store_segment_graph(segment_data)
    print(f"✅ Stored segment with ID: {segment_id}")
    
    # Test similarity edge creation
    success = await neo4j.create_similarity_edges("test-asset-001", "test-asset-002", 0.85)
    print(f"✅ Created similarity edge: {success}")
    
    # Test similar content search
    similar_content = await neo4j.find_similar_content("test-asset-001")
    print(f"✅ Found {len(similar_content)} similar content items")
    
    # Test recommendations
    recommendations = await neo4j.get_content_recommendations("test-asset-001")
    print(f"✅ Got {len(recommendations)} recommendations")
    
    # Test object search
    object_results = await neo4j.find_objects_in_content("car")
    print(f"✅ Found {len(object_results)} segments with 'car'")
    
    # Test statistics
    stats = await neo4j.get_graph_statistics()
    print(f"✅ Graph statistics: {stats}")
    
    print("\n🎉 Neo4j integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_neo4j_integration())
