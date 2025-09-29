"""
DataFlux Neo4j Client
Python client for Neo4j graph database operations
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Neo4jConfig:
    """Neo4j configuration"""
    url: str = "http://localhost:2007"
    username: str = "neo4j"
    password: str = "dataflux_pass"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

class Neo4jClient:
    """Client for Neo4j graph database operations"""
    
    def __init__(self, config: Neo4jConfig = None):
        self.config = config or Neo4jConfig()
        self.auth = (self.config.username, self.config.password)
        self.base_url = f"{self.config.url}/db/data"
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = requests.request(
                    method, 
                    url, 
                    auth=self.auth,
                    timeout=self.config.timeout,
                    **kwargs
                )
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.config.retry_attempts - 1:
                    raise e
                time.sleep(self.config.retry_delay * (2 ** attempt))
        
        raise requests.exceptions.RequestException("Max retries exceeded")
    
    def health_check(self) -> bool:
        """Check if Neo4j is healthy"""
        try:
            response = self._make_request("GET", "/")
            return response.status_code == 200
        except:
            return False
    
    def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        url = f"{self.base_url}/transaction/commit"
        
        payload = {
            "statements": [
                {
                    "statement": query,
                    "parameters": parameters or {}
                }
            ]
        }
        
        try:
            response = self._make_request(
                "POST",
                "/transaction/commit",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "results" in result and result["results"]:
                    return result["results"][0]["data"]
                return []
            else:
                print(f"❌ Query failed: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error executing query: {e}")
            return []
    
    def create_node(self, labels: List[str], properties: Dict[str, Any]) -> Optional[str]:
        """Create a node with labels and properties"""
        labels_str = ":".join(labels)
        properties_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        
        query = f"CREATE (n:{labels_str} {{{properties_str}}}) RETURN id(n) as node_id"
        
        result = self.execute_cypher(query, properties)
        if result and result[0]["row"]:
            return str(result[0]["row"][0])
        return None
    
    def create_relationship(self, from_node_id: str, to_node_id: str, 
                          relationship_type: str, properties: Dict[str, Any] = None) -> bool:
        """Create a relationship between two nodes"""
        rel_props = ""
        if properties:
            rel_props = " {" + ", ".join([f"{k}: ${k}" for k in properties.keys()]) + "}"
        
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:{relationship_type}{rel_props}]->(b)
        RETURN r
        """
        
        params = {"from_id": int(from_node_id), "to_id": int(to_node_id)}
        if properties:
            params.update(properties)
        
        result = self.execute_cypher(query, params)
        return len(result) > 0
    
    def find_nodes(self, labels: List[str] = None, properties: Dict[str, Any] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """Find nodes by labels and properties"""
        labels_str = ":".join(labels) if labels else ""
        where_clause = ""
        
        if properties:
            conditions = [f"n.{k} = ${k}" for k in properties.keys()]
            where_clause = f"WHERE {' AND '.join(conditions)}"
        
        query = f"MATCH (n{':' + labels_str if labels_str else ''}) {where_clause} RETURN n LIMIT {limit}"
        
        result = self.execute_cypher(query, properties or {})
        return [row["row"][0] for row in result]
    
    def find_relationships(self, from_labels: List[str] = None, to_labels: List[str] = None,
                          relationship_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Find relationships between nodes"""
        from_str = ":".join(from_labels) if from_labels else ""
        to_str = ":".join(to_labels) if to_labels else ""
        rel_str = f":{relationship_type}" if relationship_type else ""
        
        query = f"""
        MATCH (a{':' + from_str if from_str else ''})-[r{rel_str}]->(b{':' + to_str if to_str else ''})
        RETURN a, r, b LIMIT {limit}
        """
        
        result = self.execute_cypher(query)
        return [{"from": row["row"][0], "relationship": row["row"][1], "to": row["row"][2]} for row in result]
    
    def find_similar_assets(self, asset_id: str, similarity_threshold: float = 0.7,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """Find assets similar to a given asset"""
        query = """
        MATCH (a1:Asset {asset_id: $asset_id})-[r:SIMILAR_TO]->(a2:Asset)
        WHERE r.similarity_score >= $threshold
        RETURN a2.asset_id, a2.filename, a2.mime_type, r.similarity_score
        ORDER BY r.similarity_score DESC
        LIMIT $limit
        """
        
        result = self.execute_cypher(query, {
            "asset_id": asset_id,
            "threshold": similarity_threshold,
            "limit": limit
        })
        
        return [{
            "asset_id": row["row"][0],
            "filename": row["row"][1],
            "mime_type": row["row"][2],
            "similarity_score": row["row"][3]
        } for row in result]
    
    def find_asset_segments(self, asset_id: str) -> List[Dict[str, Any]]:
        """Find all segments of an asset"""
        query = """
        MATCH (a:Asset {asset_id: $asset_id})-[:CONTAINS]->(s:Segment)
        RETURN s.segment_id, s.segment_type, s.sequence_number, 
               s.start_time, s.end_time, s.content_description
        ORDER BY s.sequence_number
        """
        
        result = self.execute_cypher(query, {"asset_id": asset_id})
        
        return [{
            "segment_id": row["row"][0],
            "segment_type": row["row"][1],
            "sequence_number": row["row"][2],
            "start_time": row["row"][3],
            "end_time": row["row"][4],
            "content_description": row["row"][5]
        } for row in result]
    
    def find_objects_in_segments(self, object_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Find segments containing a specific object"""
        query = """
        MATCH (s:Segment)
        WHERE $object_name IN s.detected_objects
        MATCH (a:Asset)-[:CONTAINS]->(s)
        RETURN s.segment_id, s.content_description, s.detected_objects,
               a.asset_id, a.filename
        ORDER BY s.confidence_score DESC
        LIMIT $limit
        """
        
        result = self.execute_cypher(query, {
            "object_name": object_name,
            "limit": limit
        })
        
        return [{
            "segment_id": row["row"][0],
            "content_description": row["row"][1],
            "detected_objects": row["row"][2],
            "asset_id": row["row"][3],
            "filename": row["row"][4]
        } for row in result]
    
    def create_similarity_relationship(self, asset1_id: str, asset2_id: str,
                                    similarity_score: float, similarity_type: str = "content") -> bool:
        """Create a similarity relationship between two assets"""
        query = """
        MATCH (a1:Asset {asset_id: $asset1_id}), (a2:Asset {asset_id: $asset2_id})
        CREATE (a1)-[:SIMILAR_TO {
            similarity_score: $score,
            similarity_type: $type,
            created_at: datetime(),
            metadata: '{"algorithm": "content_similarity"}'
        }]->(a2)
        RETURN a1, a2
        """
        
        result = self.execute_cypher(query, {
            "asset1_id": asset1_id,
            "asset2_id": asset2_id,
            "score": similarity_score,
            "type": similarity_type
        })
        
        return len(result) > 0
    
    def get_recommendations(self, asset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get content recommendations based on similarity"""
        query = """
        MATCH (a1:Asset {asset_id: $asset_id})-[r:SIMILAR_TO]->(a2:Asset)
        WHERE r.similarity_score >= 0.6
        RETURN a2.asset_id, a2.filename, a2.mime_type, a2.tags,
               r.similarity_score, r.similarity_type
        ORDER BY r.similarity_score DESC
        LIMIT $limit
        """
        
        result = self.execute_cypher(query, {
            "asset_id": asset_id,
            "limit": limit
        })
        
        return [{
            "asset_id": row["row"][0],
            "filename": row["row"][1],
            "mime_type": row["row"][2],
            "tags": row["row"][3],
            "similarity_score": row["row"][4],
            "similarity_type": row["row"][5]
        } for row in result]
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph database statistics"""
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->()
        RETURN 
            labels(n)[0] as label,
            count(n) as count,
            count(r) as relationships
        ORDER BY count DESC
        """
        
        result = self.execute_cypher(query)
        
        stats = {
            "total_nodes": 0,
            "total_relationships": 0,
            "by_label": {}
        }
        
        for row in result:
            label = row["row"][0]
            count = row["row"][1]
            relationships = row["row"][2]
            
            stats["total_nodes"] += count
            stats["total_relationships"] += relationships
            stats["by_label"][label] = {
                "nodes": count,
                "relationships": relationships
            }
        
        return stats

# Mock implementation for testing without Neo4j
class MockNeo4jClient:
    """Mock Neo4j client for testing"""
    
    def __init__(self, config: Neo4jConfig = None):
        self.nodes = {}
        self.relationships = []
        self.node_counter = 0
        
    def health_check(self) -> bool:
        return True
    
    def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Mock Cypher execution"""
        print(f"🔍 Mock Cypher Query: {query[:100]}...")
        return []
    
    def create_node(self, labels: List[str], properties: Dict[str, Any]) -> Optional[str]:
        """Mock node creation"""
        node_id = str(self.node_counter)
        self.node_counter += 1
        
        self.nodes[node_id] = {
            "labels": labels,
            "properties": properties
        }
        
        print(f"✅ Mock created node {node_id} with labels {labels}")
        return node_id
    
    def create_relationship(self, from_node_id: str, to_node_id: str, 
                          relationship_type: str, properties: Dict[str, Any] = None) -> bool:
        """Mock relationship creation"""
        self.relationships.append({
            "from": from_node_id,
            "to": to_node_id,
            "type": relationship_type,
            "properties": properties or {}
        })
        
        print(f"✅ Mock created relationship {relationship_type} from {from_node_id} to {to_node_id}")
        return True
    
    def find_similar_assets(self, asset_id: str, similarity_threshold: float = 0.7,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """Mock similar assets search"""
        print(f"🔍 Mock finding similar assets to {asset_id}")
        return []
    
    def get_recommendations(self, asset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Mock recommendations"""
        print(f"🔍 Mock getting recommendations for {asset_id}")
        return []

# Test function
def test_neo4j_client():
    """Test the Neo4j client"""
    print("🧪 Testing Neo4j Client")
    print("=" * 40)
    
    # Use mock implementation for testing
    client = MockNeo4jClient()
    
    # Test connection
    print(f"✅ Neo4j health check: {client.health_check()}")
    
    # Test node creation
    asset_id = client.create_node(
        ["Asset", "Entity"],
        {
            "entity_id": "test-asset-001",
            "asset_id": "test-asset-001",
            "filename": "test_video.mp4",
            "mime_type": "video/mp4",
            "processing_status": "completed"
        }
    )
    print(f"✅ Created asset with ID: {asset_id}")
    
    # Test relationship creation
    segment_id = client.create_node(
        ["Segment", "Entity"],
        {
            "entity_id": "test-segment-001",
            "segment_id": "test-segment-001",
            "asset_id": "test-asset-001",
            "segment_type": "scene"
        }
    )
    
    success = client.create_relationship(
        asset_id, segment_id, "CONTAINS",
        {"relationship_type": "contains", "sequence": 1}
    )
    print(f"✅ Created relationship: {success}")
    
    # Test similarity search
    similar_assets = client.find_similar_assets("test-asset-001")
    print(f"✅ Found {len(similar_assets)} similar assets")
    
    # Test recommendations
    recommendations = client.get_recommendations("test-asset-001")
    print(f"✅ Got {len(recommendations)} recommendations")
    
    print("\n🎉 Neo4j client test completed!")

if __name__ == "__main__":
    test_neo4j_client()
