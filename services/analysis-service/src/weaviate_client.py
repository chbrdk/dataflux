"""
DataFlux Weaviate Client
Python client for Weaviate vector database operations
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WeaviateConfig:
    """Weaviate configuration"""
    url: str = "http://localhost:2005"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

class WeaviateClient:
    """Client for Weaviate vector database operations"""
    
    def __init__(self, config: WeaviateConfig = None):
        self.config = config or WeaviateConfig()
        self.client_url = f"{self.config.url}/v1"
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        url = f"{self.client_url}{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = requests.request(
                    method, 
                    url, 
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
        """Check if Weaviate is healthy"""
        try:
            response = self._make_request("GET", "/meta")
            return response.status_code == 200
        except:
            return False
    
    def create_object(self, class_name: str, properties: Dict[str, Any], 
                     vector: Optional[List[float]] = None) -> Optional[str]:
        """Create a new object in Weaviate"""
        data = {
            "class": class_name,
            "properties": properties
        }
        
        if vector:
            data["vector"] = vector
        
        try:
            response = self._make_request(
                "POST", 
                "/objects",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("id")
            else:
                print(f"❌ Failed to create object: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating object: {e}")
            return None
    
    def get_object(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Get an object by ID"""
        try:
            response = self._make_request("GET", f"/objects/{object_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting object: {e}")
            return None
    
    def update_object(self, object_id: str, properties: Dict[str, Any],
                     vector: Optional[List[float]] = None) -> bool:
        """Update an existing object"""
        data = {"properties": properties}
        
        if vector:
            data["vector"] = vector
        
        try:
            response = self._make_request(
                "PATCH",
                f"/objects/{object_id}",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error updating object: {e}")
            return False
    
    def delete_object(self, object_id: str) -> bool:
        """Delete an object by ID"""
        try:
            response = self._make_request("DELETE", f"/objects/{object_id}")
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error deleting object: {e}")
            return False
    
    def search_objects(self, class_name: str, query: str = None,
                      vector: Optional[List[float]] = None,
                      limit: int = 10, offset: int = 0,
                      where_filter: Optional[Dict[str, Any]] = None,
                      hybrid: bool = False) -> List[Dict[str, Any]]:
        """Search for objects using text or vector similarity"""
        
        # Build the search query
        search_data = {
            "class": class_name,
            "limit": limit,
            "offset": offset
        }
        
        if hybrid and query and vector:
            # Hybrid search (text + vector)
            search_data.update({
                "query": query,
                "vector": vector,
                "fusionType": "relativeScoreFusion"
            })
        elif vector:
            # Vector similarity search
            search_data["vector"] = vector
        elif query:
            # Text search
            search_data["query"] = query
        
        if where_filter:
            search_data["where"] = where_filter
        
        try:
            response = self._make_request(
                "POST",
                "/graphql",
                json={
                    "query": """
                    query($class: String!, $query: String, $vector: [Float], $limit: Int, $offset: Int, $where: WhereFilter) {
                        Get {
                            %s(
                                limit: $limit
                                offset: $offset
                                %s
                                %s
                                %s
                            ) {
                                _additional {
                                    id
                                    distance
                                    score
                                }
                                ... on %s {
                                    entity_id
                                    filename
                                    mime_type
                                    file_size
                                    processing_status
                                    created_at
                                    metadata
                                    tags
                                    collection_id
                                }
                            }
                        }
                    }
                    """ % (
                        class_name,
                        'bm25: {query: $query}' if query else '',
                        'nearVector: {vector: $vector}' if vector else '',
                        'where: $where' if where_filter else '',
                        class_name
                    ),
                    "variables": search_data
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "data" in result and "Get" in result["data"]:
                    return result["data"]["Get"].get(class_name, [])
                return []
            else:
                print(f"❌ Search failed: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error searching objects: {e}")
            return []
    
    def get_similar_objects(self, class_name: str, object_id: str,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """Get objects similar to a given object"""
        try:
            response = self._make_request(
                "POST",
                "/graphql",
                json={
                    "query": """
                    query($class: String!, $id: String!, $limit: Int) {
                        Get {
                            %s(
                                nearObject: {id: $id}
                                limit: $limit
                            ) {
                                _additional {
                                    id
                                    distance
                                }
                                ... on %s {
                                    entity_id
                                    filename
                                    mime_type
                                    file_size
                                    processing_status
                                    created_at
                                    metadata
                                    tags
                                    collection_id
                                }
                            }
                        }
                    }
                    """ % (class_name, class_name),
                    "variables": {
                        "class": class_name,
                        "id": object_id,
                        "limit": limit
                    }
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "data" in result and "Get" in result["data"]:
                    return result["data"]["Get"].get(class_name, [])
                return []
            else:
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting similar objects: {e}")
            return []
    
    def batch_create_objects(self, class_name: str, objects: List[Dict[str, Any]]) -> List[str]:
        """Create multiple objects in a batch"""
        created_ids = []
        
        for obj_data in objects:
            properties = obj_data.get("properties", {})
            vector = obj_data.get("vector")
            
            obj_id = self.create_object(class_name, properties, vector)
            if obj_id:
                created_ids.append(obj_id)
        
        return created_ids
    
    def get_class_info(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific class"""
        try:
            response = self._make_request("GET", f"/schema/{class_name}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting class info: {e}")
            return None
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the complete schema"""
        try:
            response = self._make_request("GET", "/schema")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting schema: {e}")
            return {}

# Convenience functions for DataFlux operations
def create_asset_embedding(client: WeaviateClient, asset_data: Dict[str, Any], 
                          embedding: List[float]) -> Optional[str]:
    """Create an asset with embedding in Weaviate"""
    return client.create_object("Asset", asset_data, embedding)

def create_segment_embedding(client: WeaviateClient, segment_data: Dict[str, Any],
                           embedding: List[float]) -> Optional[str]:
    """Create a segment with embedding in Weaviate"""
    return client.create_object("Segment", segment_data, embedding)

def create_feature_embedding(client: WeaviateClient, feature_data: Dict[str, Any],
                           embedding: List[float]) -> Optional[str]:
    """Create a feature with embedding in Weaviate"""
    return client.create_object("Feature", feature_data, embedding)

def search_similar_assets(client: WeaviateClient, query_vector: List[float],
                         limit: int = 10, collection_id: str = None) -> List[Dict[str, Any]]:
    """Search for similar assets using vector similarity"""
    where_filter = None
    if collection_id:
        where_filter = {
            "path": ["collection_id"],
            "operator": "Equal",
            "valueString": collection_id
        }
    
    return client.search_objects(
        "Asset", 
        vector=query_vector, 
        limit=limit, 
        where_filter=where_filter
    )

def hybrid_search_assets(client: WeaviateClient, query_text: str, 
                        query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
    """Perform hybrid search (text + vector) on assets"""
    return client.search_objects(
        "Asset",
        query=query_text,
        vector=query_vector,
        limit=limit,
        hybrid=True
    )
