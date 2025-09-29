#!/usr/bin/env python3
"""
DataFlux Neo4j Schema Setup
Creates the graph database schema for relationships and similarity edges
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional

class Neo4jSchemaManager:
    def __init__(self, neo4j_url: str = "http://localhost:2007", 
                 username: str = "neo4j", password: str = "dataflux_pass"):
        self.neo4j_url = neo4j_url
        self.username = username
        self.password = password
        self.auth = (username, password)
        
    def wait_for_neo4j(self, max_attempts: int = 30) -> bool:
        """Wait for Neo4j to be ready"""
        print("⏳ Waiting for Neo4j to be ready...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.neo4j_url}/db/data/", 
                                     auth=self.auth, timeout=5)
                if response.status_code == 200:
                    print("✅ Neo4j is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print(f"⏳ Attempt {attempt + 1}/{max_attempts}: Neo4j not ready yet...")
            time.sleep(2)
        
        print("❌ Neo4j failed to start after maximum attempts")
        return False
    
    def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a Cypher query"""
        url = f"{self.neo4j_url}/db/data/transaction/commit"
        
        payload = {
            "statements": [
                {
                    "statement": query,
                    "parameters": parameters or {}
                }
            ]
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Query failed: {response.status_code}")
                print(f"Response: {response.text}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error executing query: {e}")
            return {}
    
    def create_constraints_and_indexes(self) -> bool:
        """Create constraints and indexes"""
        print("🔧 Creating constraints and indexes...")
        
        constraints_and_indexes = [
            # Constraints
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE CONSTRAINT asset_id_unique IF NOT EXISTS FOR (a:Asset) REQUIRE a.asset_id IS UNIQUE",
            "CREATE CONSTRAINT segment_id_unique IF NOT EXISTS FOR (s:Segment) REQUIRE s.segment_id IS UNIQUE",
            "CREATE CONSTRAINT collection_id_unique IF NOT EXISTS FOR (c:Collection) REQUIRE c.collection_id IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX asset_mime_type_index IF NOT EXISTS FOR (a:Asset) ON (a.mime_type)",
            "CREATE INDEX asset_status_index IF NOT EXISTS FOR (a:Asset) ON (a.processing_status)",
            "CREATE INDEX segment_type_index IF NOT EXISTS FOR (s:Segment) ON (s.segment_type)",
            "CREATE INDEX relationship_type_index IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.relationship_type)",
            "CREATE INDEX similarity_score_index IF NOT EXISTS FOR ()-[r:SIMILAR_TO]-() ON (r.similarity_score)",
        ]
        
        for query in constraints_and_indexes:
            result = self.execute_cypher(query)
            if not result:
                print(f"❌ Failed to execute: {query}")
                return False
        
        print("✅ Constraints and indexes created successfully!")
        return True
    
    def create_sample_data(self) -> bool:
        """Create sample data for testing"""
        print("🧪 Creating sample data...")
        
        # Create sample entities
        sample_queries = [
            # Create Collections
            """
            CREATE (c:Collection {
                collection_id: 'default',
                name: 'Default Collection',
                description: 'Default collection for all assets',
                created_at: datetime(),
                updated_at: datetime()
            })
            """,
            
            # Create sample Assets
            """
            CREATE (a1:Asset:Entity {
                entity_id: 'asset-001',
                asset_id: 'asset-001',
                filename: 'sample_video.mp4',
                mime_type: 'video/mp4',
                file_size: 1024000,
                processing_status: 'completed',
                created_at: datetime(),
                updated_at: datetime(),
                metadata: '{"duration": 120.5, "resolution": "1920x1080"}',
                tags: ['video', 'sample', 'test'],
                collection_id: 'default'
            })
            """,
            
            """
            CREATE (a2:Asset:Entity {
                entity_id: 'asset-002',
                asset_id: 'asset-002',
                filename: 'sample_image.jpg',
                mime_type: 'image/jpeg',
                file_size: 512000,
                processing_status: 'completed',
                created_at: datetime(),
                updated_at: datetime(),
                metadata: '{"width": 1920, "height": 1080}',
                tags: ['image', 'sample', 'test'],
                collection_id: 'default'
            })
            """,
            
            # Create sample Segments
            """
            CREATE (s1:Segment:Entity {
                entity_id: 'segment-001',
                segment_id: 'segment-001',
                asset_id: 'asset-001',
                segment_type: 'scene',
                sequence_number: 1,
                start_time: 0.0,
                end_time: 10.0,
                confidence_score: 0.95,
                content_description: 'Opening scene with car',
                detected_objects: ['car', 'road', 'sky'],
                detected_text: '',
                created_at: datetime(),
                updated_at: datetime()
            })
            """,
            
            """
            CREATE (s2:Segment:Entity {
                entity_id: 'segment-002',
                segment_id: 'segment-002',
                asset_id: 'asset-001',
                segment_type: 'scene',
                sequence_number: 2,
                start_time: 10.0,
                end_time: 20.0,
                confidence_score: 0.88,
                content_description: 'Car driving on highway',
                detected_objects: ['car', 'highway', 'trees'],
                detected_text: '',
                created_at: datetime(),
                updated_at: datetime()
            })
            """,
            
            # Create relationships
            """
            MATCH (a1:Asset {asset_id: 'asset-001'}), (s1:Segment {segment_id: 'segment-001'})
            CREATE (a1)-[:CONTAINS {
                relationship_type: 'contains',
                created_at: datetime(),
                metadata: '{"sequence": 1}'
            }]->(s1)
            """,
            
            """
            MATCH (a1:Asset {asset_id: 'asset-001'}), (s2:Segment {segment_id: 'segment-002'})
            CREATE (a1)-[:CONTAINS {
                relationship_type: 'contains',
                created_at: datetime(),
                metadata: '{"sequence": 2}'
            }]->(s2)
            """,
            
            # Create similarity relationships
            """
            MATCH (a1:Asset {asset_id: 'asset-001'}), (a2:Asset {asset_id: 'asset-002'})
            CREATE (a1)-[:SIMILAR_TO {
                similarity_score: 0.75,
                similarity_type: 'content',
                created_at: datetime(),
                metadata: '{"algorithm": "visual_similarity"}'
            }]->(a2)
            """,
            
            """
            MATCH (s1:Segment {segment_id: 'segment-001'}), (s2:Segment {segment_id: 'segment-002'})
            CREATE (s1)-[:SIMILAR_TO {
                similarity_score: 0.82,
                similarity_type: 'visual',
                created_at: datetime(),
                metadata: '{"algorithm": "scene_similarity"}'
            }]->(s2)
            """,
            
            # Create collection relationships
            """
            MATCH (c:Collection {collection_id: 'default'}), (a1:Asset {asset_id: 'asset-001'})
            CREATE (c)-[:CONTAINS {
                relationship_type: 'contains',
                created_at: datetime()
            }]->(a1)
            """,
            
            """
            MATCH (c:Collection {collection_id: 'default'}), (a2:Asset {asset_id: 'asset-002'})
            CREATE (c)-[:CONTAINS {
                relationship_type: 'contains',
                created_at: datetime()
            }]->(a2)
            """
        ]
        
        for query in sample_queries:
            result = self.execute_cypher(query)
            if not result:
                print(f"❌ Failed to execute: {query}")
                return False
        
        print("✅ Sample data created successfully!")
        return True
    
    def test_queries(self) -> bool:
        """Test various graph queries"""
        print("🧪 Testing graph queries...")
        
        test_queries = [
            {
                "name": "Count all nodes",
                "query": "MATCH (n) RETURN count(n) as total_nodes"
            },
            {
                "name": "Count all relationships",
                "query": "MATCH ()-[r]->() RETURN count(r) as total_relationships"
            },
            {
                "name": "Find assets with segments",
                "query": """
                MATCH (a:Asset)-[:CONTAINS]->(s:Segment)
                RETURN a.filename, collect(s.segment_type) as segment_types
                """
            },
            {
                "name": "Find similar assets",
                "query": """
                MATCH (a1:Asset)-[r:SIMILAR_TO]->(a2:Asset)
                WHERE r.similarity_score > 0.7
                RETURN a1.filename, a2.filename, r.similarity_score
                ORDER BY r.similarity_score DESC
                """
            },
            {
                "name": "Find segments by detected objects",
                "query": """
                MATCH (s:Segment)
                WHERE 'car' IN s.detected_objects
                RETURN s.segment_id, s.content_description, s.detected_objects
                """
            }
        ]
        
        for test in test_queries:
            result = self.execute_cypher(test["query"])
            if result and "results" in result and result["results"]:
                print(f"✅ {test['name']}: {result['results'][0]['data']}")
            else:
                print(f"❌ {test['name']} failed")
                return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats_query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->()
        RETURN 
            labels(n)[0] as label,
            count(n) as count,
            count(r) as relationships
        ORDER BY count DESC
        """
        
        result = self.execute_cypher(stats_query)
        if result and "results" in result and result["results"]:
            return {
                "statistics": result["results"][0]["data"],
                "total_nodes": sum(row["row"][1] for row in result["results"][0]["data"]),
                "total_relationships": sum(row["row"][2] for row in result["results"][0]["data"])
            }
        return {}

def main():
    """Main function to set up Neo4j schema"""
    print("🚀 DataFlux Neo4j Schema Setup")
    print("=" * 50)
    
    manager = Neo4jSchemaManager()
    
    # Wait for Neo4j to be ready
    if not manager.wait_for_neo4j():
        print("❌ Cannot proceed without Neo4j")
        return False
    
    # Create constraints and indexes
    if not manager.create_constraints_and_indexes():
        print("❌ Failed to create constraints and indexes")
        return False
    
    # Create sample data
    if not manager.create_sample_data():
        print("❌ Failed to create sample data")
        return False
    
    # Test queries
    if not manager.test_queries():
        print("❌ Query tests failed")
        return False
    
    # Get statistics
    stats = manager.get_statistics()
    if stats:
        print(f"\n📊 Database Statistics:")
        print(f"  Total Nodes: {stats.get('total_nodes', 0)}")
        print(f"  Total Relationships: {stats.get('total_relationships', 0)}")
    
    print("\n🎉 Neo4j schema setup completed successfully!")
    print("📊 Schema elements created:")
    print("  - Nodes: Entity, Asset, Segment, Collection")
    print("  - Relationships: CONTAINS, SIMILAR_TO")
    print("  - Constraints: Unique IDs for all entities")
    print("  - Indexes: Performance indexes on key properties")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
