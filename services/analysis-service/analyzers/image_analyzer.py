"""
Image Analyzer for DataFlux Analysis Service
"""

import asyncio
import logging
from typing import Dict, List, Any
import cv2
import numpy as np
from PIL import Image

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)

class ImageAnalyzer(BaseAnalyzer):
    """Image content analyzer with object detection and feature extraction"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/bmp', 'image/tiff', 'image/webp'
        ]
    
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image file"""
        self.log_analysis_start(file_path, asset_data)
        
        try:
            if not self.validate_file(file_path):
                return self.create_error_result("Invalid file")
            
            # Run analysis tasks
            tasks = [
                self._analyze_image_properties(file_path),
                self._detect_objects(file_path),
                self._extract_colors(file_path),
                self._detect_text(file_path)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            segments = []
            features = []
            embeddings = []
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Image analysis task failed", error=str(result))
                    continue
                
                if isinstance(result, dict):
                    segments.extend(result.get('segments', []))
                    features.extend(result.get('features', []))
                    embeddings.extend(result.get('embeddings', []))
            
            result = self.create_success_result(
                segments=segments,
                features=features,
                embeddings=embeddings,
                metadata={
                    'image_info': await self._get_image_info(file_path)
                }
            )
            
            self.log_analysis_end(file_path, result)
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed", error=str(e))
            return self.create_error_result(str(e))
    
    async def _analyze_image_properties(self, file_path: str) -> Dict[str, Any]:
        """Analyze basic image properties"""
        try:
            with Image.open(file_path) as img:
                features = [{
                    'type': 'image_properties',
                    'domain': 'visual',
                    'confidence': 1.0,
                    'data': {
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                        'size': img.size
                    },
                    'metadata': {'analyzer': 'image_properties'}
                }]
                
                return {
                    'segments': [],
                    'features': features,
                    'embeddings': []
                }
                
        except Exception as e:
            logger.error(f"Image properties analysis failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _detect_objects(self, file_path: str) -> Dict[str, Any]:
        """Detect objects in image"""
        try:
            img = cv2.imread(file_path)
            if img is None:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            detected_objects = []
            
            # Face detection
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in faces:
                detected_objects.append({
                    'type': 'face',
                    'bbox': [x, y, w, h],
                    'confidence': 0.8
                })
            
            # Create features
            features = []
            if detected_objects:
                features.append({
                    'type': 'object_detection',
                    'domain': 'visual',
                    'confidence': 0.8,
                    'data': {
                        'objects': detected_objects,
                        'count': len(detected_objects)
                    },
                    'metadata': {'analyzer': 'object_detection'}
                })
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Object detection failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _extract_colors(self, file_path: str) -> Dict[str, Any]:
        """Extract dominant colors from image"""
        try:
            img = cv2.imread(file_path)
            if img is None:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            # Convert to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Reshape image to be a list of pixels
            pixels = img_rgb.reshape(-1, 3)
            
            # Calculate dominant colors using k-means
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=5, random_state=42)
            kmeans.fit(pixels)
            
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            
            # Count color frequencies
            color_counts = {}
            for label in labels:
                color_counts[label] = color_counts.get(label, 0) + 1
            
            # Create color features
            dominant_colors = []
            for i, color in enumerate(colors):
                dominant_colors.append({
                    'rgb': color.tolist(),
                    'frequency': color_counts[i] / len(labels)
                })
            
            features = [{
                'type': 'dominant_colors',
                'domain': 'visual',
                'confidence': 0.9,
                'data': {
                    'colors': dominant_colors,
                    'count': len(dominant_colors)
                },
                'metadata': {'analyzer': 'color_extraction'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Color extraction failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _detect_text(self, file_path: str) -> Dict[str, Any]:
        """Detect text in image using OCR"""
        try:
            # For now, return mock OCR results
            # In production, use pytesseract or easyocr
            
            features = [{
                'type': 'text_detection',
                'domain': 'text',
                'confidence': 0.6,
                'data': {
                    'has_text': False,  # Mock result
                    'text_regions': []
                },
                'metadata': {'analyzer': 'ocr'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Text detection failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _get_image_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic image information"""
        try:
            with Image.open(file_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
        except Exception as e:
            logger.error(f"Failed to get image info", error=str(e))
            return {}
