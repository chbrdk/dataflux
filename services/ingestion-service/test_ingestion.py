"""
Test script for DataFlux Ingestion Service
"""

import requests
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8001"
TEST_FILE_PATH = "test_sample.mp4"

def create_test_file():
    """Create a test video file"""
    test_content = b"fake video content for testing" * 1000  # ~30KB
    with open(TEST_FILE_PATH, "wb") as f:
        f.write(test_content)
    return TEST_FILE_PATH

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_upload():
    """Test file upload"""
    print("\nTesting file upload...")
    
    # Create test file
    test_file = create_test_file()
    
    # Upload file
    with open(test_file, "rb") as f:
        files = {"file": (test_file, f, "video/mp4")}
        data = {
            "context": "Test upload",
            "priority": 5,
            "collection_id": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/assets",
            files=files,
            data=data
        )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Clean up test file
    Path(test_file).unlink(missing_ok=True)
    
    return response.status_code == 200, response.json().get("id") if response.status_code == 200 else None

def test_get_asset(asset_id):
    """Test get asset endpoint"""
    print(f"\nTesting get asset {asset_id}...")
    response = requests.get(f"{BASE_URL}/api/v1/assets/{asset_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_list_assets():
    """Test list assets endpoint"""
    print("\nTesting list assets...")
    response = requests.get(f"{BASE_URL}/api/v1/assets?limit=10")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_status(asset_id):
    """Test status endpoint"""
    print(f"\nTesting status for {asset_id}...")
    response = requests.get(f"{BASE_URL}/api/v1/assets/{asset_id}/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("DataFlux Ingestion Service Tests")
    print("=" * 40)
    
    # Test health
    if not test_health():
        print("❌ Health check failed")
        return
    
    print("✅ Health check passed")
    
    # Test upload
    upload_success, asset_id = test_upload()
    if not upload_success:
        print("❌ Upload test failed")
        return
    
    print("✅ Upload test passed")
    
    # Test get asset
    if not test_get_asset(asset_id):
        print("❌ Get asset test failed")
        return
    
    print("✅ Get asset test passed")
    
    # Test list assets
    if not test_list_assets():
        print("❌ List assets test failed")
        return
    
    print("✅ List assets test passed")
    
    # Test status
    if not test_status(asset_id):
        print("❌ Status test failed")
        return
    
    print("✅ Status test passed")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    main()
