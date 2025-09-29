"""
DataFlux Ingestion Service - Unit Tests
Comprehensive unit tests for the Ingestion Service
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

# Import the service components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.main_simple import app, AssetUpload, AssetResponse
from src.metrics import IngestionMetrics

class TestIngestionService:
    """Test cases for Ingestion Service"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_file(self):
        """Create a sample test file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b"Test file content for DataFlux")
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def sample_video_file(self):
        """Create a sample video file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
            # Write minimal MP4 header
            f.write(b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom')
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_upload_asset_success(self, client, sample_file):
        """Test successful asset upload"""
        with open(sample_file, 'rb') as f:
            response = client.post(
                "/api/v1/assets",
                files={"file": ("test.txt", f, "text/plain")},
                data={"context": "Test upload", "priority": "5"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "asset_id" in data
        assert data["filename"] == "test.txt"
        assert data["mime_type"] == "text/plain"
        assert data["processing_status"] == "queued"
    
    def test_upload_asset_without_file(self, client):
        """Test upload without file"""
        response = client.post(
            "/api/v1/assets",
            data={"context": "Test upload", "priority": "5"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_upload_asset_invalid_priority(self, client, sample_file):
        """Test upload with invalid priority"""
        with open(sample_file, 'rb') as f:
            response = client.post(
                "/api/v1/assets",
                files={"file": ("test.txt", f, "text/plain")},
                data={"context": "Test upload", "priority": "invalid"}
            )
        assert response.status_code == 422
    
    def test_get_assets(self, client):
        """Test getting assets list"""
        response = client.get("/api/v1/assets")
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert isinstance(data["assets"], list)
    
    def test_get_assets_with_pagination(self, client):
        """Test getting assets with pagination"""
        response = client.get("/api/v1/assets?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
    
    def test_duplicate_detection(self, client, sample_file):
        """Test duplicate file detection"""
        # Upload first file
        with open(sample_file, 'rb') as f:
            response1 = client.post(
                "/api/v1/assets",
                files={"file": ("test.txt", f, "text/plain")},
                data={"context": "First upload", "priority": "5"}
            )
        assert response1.status_code == 200
        
        # Upload same file again
        with open(sample_file, 'rb') as f:
            response2 = client.post(
                "/api/v1/assets",
                files={"file": ("test.txt", f, "text/plain")},
                data={"context": "Duplicate upload", "priority": "5"}
            )
        assert response2.status_code == 200
        
        # Check if duplicate was detected
        data1 = response1.json()
        data2 = response2.json()
        assert data1["file_hash"] == data2["file_hash"]
    
    def test_video_file_upload(self, client, sample_video_file):
        """Test video file upload"""
        with open(sample_video_file, 'rb') as f:
            response = client.post(
                "/api/v1/assets",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"context": "Video upload", "priority": "5"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mime_type"] == "video/mp4"
        assert data["filename"] == "test.mp4"
    
    def test_large_file_handling(self, client):
        """Test handling of large files"""
        # Create a large file (simulate)
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(large_content)
            f.flush()
            
            with open(f.name, 'rb') as file:
                response = client.post(
                    "/api/v1/assets",
                    files={"file": ("large.txt", file, "text/plain")},
                    data={"context": "Large file upload", "priority": "5"}
                )
            
            os.unlink(f.name)
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_size"] > 0
    
    def test_mime_type_detection(self, client):
        """Test MIME type detection for different file types"""
        test_cases = [
            ("test.txt", "text/plain"),
            ("test.mp4", "video/mp4"),
            ("test.jpg", "image/jpeg"),
            ("test.pdf", "application/pdf"),
            ("test.zip", "application/zip"),
        ]
        
        for filename, expected_mime in test_cases:
            content = b"test content"
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[-1]}") as f:
                f.write(content)
                f.flush()
                
                with open(f.name, 'rb') as file:
                    response = client.post(
                        "/api/v1/assets",
                        files={"file": (filename, file, expected_mime)},
                        data={"context": "MIME test", "priority": "5"}
                    )
                
                os.unlink(f.name)
            
            assert response.status_code == 200
            data = response.json()
            assert data["mime_type"] == expected_mime

class TestIngestionMetrics:
    """Test cases for Ingestion Metrics"""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance"""
        return IngestionMetrics()
    
    def test_request_metrics(self, metrics):
        """Test request metrics recording"""
        metrics.record_request("POST", "/api/v1/assets", 200, 0.5)
        # Metrics are recorded internally, we can't easily test the values
        # without accessing the internal state, but we can ensure no exceptions
    
    def test_file_upload_metrics(self, metrics):
        """Test file upload metrics recording"""
        metrics.record_file_upload("video/mp4", 1024000, 2.5, "success")
        # Metrics are recorded internally
    
    def test_processing_metrics(self, metrics):
        """Test processing metrics recording"""
        metrics.record_processing("video/mp4", 10.0, "success")
        metrics.record_processing("image/jpeg", 5.0, "failed")
        # Metrics are recorded internally
    
    def test_storage_metrics(self, metrics):
        """Test storage metrics recording"""
        metrics.record_storage_operation("upload", 1.0, "success")
        metrics.record_storage_operation("download", 0.5, "success")
        # Metrics are recorded internally
    
    def test_database_metrics(self, metrics):
        """Test database metrics recording"""
        metrics.record_database_operation("insert", 0.1, "success")
        metrics.record_database_operation("select", 0.05, "success")
        # Metrics are recorded internally
    
    def test_kafka_metrics(self, metrics):
        """Test Kafka metrics recording"""
        metrics.record_kafka_message("asset-processing", 0.2, "success")
        # Metrics are recorded internally
    
    def test_error_metrics(self, metrics):
        """Test error metrics recording"""
        metrics.record_error("validation_error", "ingestion_service")
        metrics.record_error("storage_error", "minio_client")
        # Metrics are recorded internally
    
    def test_system_metrics(self, metrics):
        """Test system metrics recording"""
        metrics.update_queue_size(5)
        metrics.update_active_connections(10)
        metrics.update_system_metrics(1024 * 1024 * 100, 75.5)  # 100MB, 75.5% CPU
        # Metrics are recorded internally

class TestAssetModels:
    """Test cases for Pydantic models"""
    
    def test_asset_upload_model(self):
        """Test AssetUpload model validation"""
        # Valid data
        asset_data = {
            "context": "Test context",
            "priority": 5,
            "collection_id": "default"
        }
        asset = AssetUpload(**asset_data)
        assert asset.context == "Test context"
        assert asset.priority == 5
        assert asset.collection_id == "default"
    
    def test_asset_upload_defaults(self):
        """Test AssetUpload default values"""
        asset = AssetUpload(context="Test")
        assert asset.priority == 5
        assert asset.collection_id == "default"
    
    def test_asset_upload_validation(self):
        """Test AssetUpload validation"""
        # Invalid priority
        with pytest.raises(ValueError):
            AssetUpload(context="Test", priority=15)  # Priority should be 1-10
        
        with pytest.raises(ValueError):
            AssetUpload(context="Test", priority=0)  # Priority should be 1-10
    
    def test_asset_response_model(self):
        """Test AssetResponse model"""
        asset_data = {
            "asset_id": "test-123",
            "filename": "test.txt",
            "mime_type": "text/plain",
            "file_size": 1024,
            "file_hash": "abc123",
            "processing_status": "queued",
            "created_at": "2025-09-28T20:00:00Z",
            "metadata": {"test": "data"}
        }
        asset = AssetResponse(**asset_data)
        assert asset.asset_id == "test-123"
        assert asset.filename == "test.txt"
        assert asset.mime_type == "text/plain"

# Integration tests
class TestIngestionIntegration:
    """Integration tests for Ingestion Service"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_full_upload_workflow(self, client):
        """Test complete upload workflow"""
        # Create test file
        test_content = b"Integration test content"
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(test_content)
            f.flush()
            
            # Upload file
            with open(f.name, 'rb') as file:
                upload_response = client.post(
                    "/api/v1/assets",
                    files={"file": ("integration_test.txt", file, "text/plain")},
                    data={"context": "Integration test", "priority": "5"}
                )
            
            os.unlink(f.name)
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        
        # Verify asset was created
        assert upload_data["asset_id"] is not None
        assert upload_data["filename"] == "integration_test.txt"
        assert upload_data["mime_type"] == "text/plain"
        assert upload_data["file_size"] == len(test_content)
        
        # Get assets list
        list_response = client.get("/api/v1/assets")
        assert list_response.status_code == 200
        list_data = list_response.json()
        
        # Verify asset appears in list
        asset_ids = [asset["asset_id"] for asset in list_data["assets"]]
        assert upload_data["asset_id"] in asset_ids
    
    def test_concurrent_uploads(self, client):
        """Test concurrent file uploads"""
        import threading
        import time
        
        results = []
        errors = []
        
        def upload_file(file_index):
            try:
                test_content = f"Concurrent test {file_index}".encode()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
                    f.write(test_content)
                    f.flush()
                    
                    with open(f.name, 'rb') as file:
                        response = client.post(
                            "/api/v1/assets",
                            files={"file": (f"concurrent_{file_index}.txt", file, "text/plain")},
                            data={"context": f"Concurrent test {file_index}", "priority": "5"}
                        )
                    
                    os.unlink(f.name)
                
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        # Start multiple upload threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=upload_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all uploads succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(status == 200 for status in results), f"Some uploads failed: {results}"
        assert len(results) == 5

# Performance tests
class TestIngestionPerformance:
    """Performance tests for Ingestion Service"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_upload_performance(self, client):
        """Test upload performance"""
        import time
        
        # Create test file
        test_content = b"Performance test content" * 1000  # ~25KB
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(test_content)
            f.flush()
            
            start_time = time.time()
            with open(f.name, 'rb') as file:
                response = client.post(
                    "/api/v1/assets",
                    files={"file": ("performance_test.txt", file, "text/plain")},
                    data={"context": "Performance test", "priority": "5"}
                )
            end_time = time.time()
            
            os.unlink(f.name)
        
        assert response.status_code == 200
        upload_time = end_time - start_time
        
        # Upload should complete within reasonable time (5 seconds for 25KB)
        assert upload_time < 5.0, f"Upload took too long: {upload_time:.2f}s"
    
    def test_memory_usage(self, client):
        """Test memory usage during uploads"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform multiple uploads
        for i in range(10):
            test_content = f"Memory test {i}".encode()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
                f.write(test_content)
                f.flush()
                
                with open(f.name, 'rb') as file:
                    response = client.post(
                        "/api/v1/assets",
                        files={"file": (f"memory_test_{i}.txt", file, "text/plain")},
                        data={"context": f"Memory test {i}", "priority": "5"}
                    )
                
                os.unlink(f.name)
            
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for 10 uploads)
        assert memory_increase < 50 * 1024 * 1024, f"Memory usage increased too much: {memory_increase / 1024 / 1024:.2f}MB"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
