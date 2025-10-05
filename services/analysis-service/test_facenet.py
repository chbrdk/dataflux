#!/usr/bin/env python3
"""
Test script for FaceNet integration in DataFlux Analysis Service
"""

import asyncio
import sys
import os
from pathlib import Path

# Add analyzers to path
sys.path.append(str(Path(__file__).parent))

from analyzers.facenet_analyzer import FaceNetAnalyzer
from analyzers.image_analyzer import ImageAnalyzer

async def test_facenet_standalone():
    """Test FaceNet analyzer standalone"""
    print("🧑 Testing FaceNet Analyzer Standalone...")
    
    analyzer = FaceNetAnalyzer()
    
    # Test with a sample image (you can replace with your test image)
    test_image = "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface.jpg"
    
    if os.path.exists(test_image):
        print(f"📸 Testing with image: {test_image}")
        
        result = await analyzer.analyze(test_image, {})
        
        print(f"✅ Analysis completed!")
        print(f"   Features: {len(result.get('features', []))}")
        print(f"   Embeddings: {len(result.get('embeddings', []))}")
        
        # Print face detection results
        for feature in result.get('features', []):
            if feature['type'] == 'face_detection':
                faces = feature['data'].get('faces', [])
                print(f"   🧑 Detected {len(faces)} faces")
                for i, face in enumerate(faces):
                    print(f"      Face {i}: confidence={face['confidence']:.3f}")
        
        # Print face recognition results
        for feature in result.get('features', []):
            if feature['type'] == 'face_recognition':
                recognized = feature['data'].get('recognized_faces', [])
                print(f"   🔍 Recognized {len(recognized)} faces")
                for i, face in enumerate(recognized):
                    print(f"      Face {i}: {'Known' if face['is_known_face'] else 'Unknown'}, quality: {face['face_quality']}")
        
        # Print database stats
        stats = analyzer.get_database_stats()
        print(f"   📊 Database stats: {stats}")
        
    else:
        print(f"❌ Test image not found: {test_image}")

async def test_integrated_analysis():
    """Test FaceNet integrated with ImageAnalyzer"""
    print("\n🖼️ Testing Integrated Image Analysis with FaceNet...")
    
    analyzer = ImageAnalyzer()
    
    # Test with a sample image
    test_image = "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface.jpg"
    
    if os.path.exists(test_image):
        print(f"📸 Testing with image: {test_image}")
        
        result = await analyzer.analyze(test_image, {})
        
        print(f"✅ Integrated analysis completed!")
        print(f"   Features: {len(result.get('features', []))}")
        print(f"   Embeddings: {len(result.get('embeddings', []))}")
        
        # Count different types of features
        feature_types = {}
        for feature in result.get('features', []):
            feature_type = feature['type']
            feature_types[feature_type] = feature_types.get(feature_type, 0) + 1
        
        print(f"   📊 Feature types: {feature_types}")
        
        # Show models used
        models_used = result.get('metadata', {}).get('models_used', [])
        print(f"   🤖 Models used: {models_used}")
        
    else:
        print(f"❌ Test image not found: {test_image}")

async def test_face_database():
    """Test face database functionality"""
    print("\n🗄️ Testing Face Database Functionality...")
    
    analyzer = FaceNetAnalyzer()
    
    # Wait for models to initialize
    await analyzer._initialize_models()
    
    # Test adding faces to database
    test_image = "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface.jpg"
    
    if os.path.exists(test_image):
        print(f"📸 Adding face to database from: {test_image}")
        
        success = await analyzer.add_face_to_database(test_image, "test_person")
        
        if success:
            print("✅ Face added to database successfully!")
            
            # Test recognition
            recognized = await analyzer.recognize_faces_in_image(test_image)
            print(f"🔍 Recognition test: {len(recognized)} faces recognized")
            
            # Show database stats
            stats = analyzer.get_database_stats()
            print(f"📊 Database stats: {stats}")
        else:
            print("❌ Failed to add face to database")
    else:
        print(f"❌ Test image not found: {test_image}")

async def test_multiple_images():
    """Test FaceNet with multiple images"""
    print("\n🖼️ Testing FaceNet with Multiple Images...")
    
    analyzer = FaceNetAnalyzer()
    
    # List of test images
    test_images = [
        "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface.jpg",
        "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface2.jpg",
        "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface3.jpg",
        "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-working.jpg",
        "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-success.jpg"
    ]
    
    total_faces = 0
    processed_images = 0
    
    for i, test_image in enumerate(test_images):
        if os.path.exists(test_image):
            print(f"📸 Processing image {i+1}/{len(test_images)}: {os.path.basename(test_image)}")
            
            result = await analyzer.analyze(test_image, {})
            
            # Count faces in this image
            faces_in_image = 0
            for feature in result.get('features', []):
                if feature['type'] == 'face_detection':
                    faces_in_image = feature['data'].get('total_faces', 0)
                    break
            
            total_faces += faces_in_image
            processed_images += 1
            
            print(f"   🧑 Found {faces_in_image} faces")
        else:
            print(f"   ❌ Image not found: {test_image}")
    
    print(f"\n📊 Summary:")
    print(f"   Processed images: {processed_images}/{len(test_images)}")
    print(f"   Total faces detected: {total_faces}")
    print(f"   Average faces per image: {total_faces/processed_images if processed_images > 0 else 0:.1f}")

async def test_performance():
    """Test FaceNet performance"""
    print("\n⚡ Testing FaceNet Performance...")
    
    analyzer = FaceNetAnalyzer()
    
    test_image = "/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/test-deepface.jpg"
    
    if os.path.exists(test_image):
        print(f"📸 Performance test with: {test_image}")
        
        # Warm up
        print("🔥 Warming up models...")
        await analyzer._initialize_models()
        
        # Performance test
        import time
        times = []
        
        for i in range(5):
            start_time = time.time()
            result = await analyzer.analyze(test_image, {})
            end_time = time.time()
            
            duration = end_time - start_time
            times.append(duration)
            
            print(f"   Run {i+1}: {duration:.2f}s")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 Performance Results:")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Min time: {min_time:.2f}s")
        print(f"   Max time: {max_time:.2f}s")
        print(f"   Device: {analyzer.device}")
        
    else:
        print(f"❌ Test image not found: {test_image}")

async def main():
    """Main test function"""
    print("🚀 Starting FaceNet Integration Tests...")
    print("=" * 60)
    
    try:
        # Test 1: Standalone FaceNet
        await test_facenet_standalone()
        
        # Test 2: Integrated analysis
        await test_integrated_analysis()
        
        # Test 3: Face database
        await test_face_database()
        
        # Test 4: Multiple images
        await test_multiple_images()
        
        # Test 5: Performance
        await test_performance()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
