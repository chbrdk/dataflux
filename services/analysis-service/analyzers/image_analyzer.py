"""
Comprehensive Image Analyzer for DataFlux Analysis Service
Implements complete image analysis with multiple AI models and computer vision techniques
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ExifTags
import base64
from io import BytesIO

# AI/ML imports
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import torch
    import clip
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    torch = None

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from sklearn.cluster import KMeans
try:
    from .base import BaseAnalyzer
except ImportError:
    # Fallback for direct import
    class BaseAnalyzer:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class ImageAnalyzer(BaseAnalyzer):
    """Comprehensive image analyzer with multiple AI models and computer vision techniques"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/bmp', 'image/tiff', 'image/webp', 'image/raw'
        ]
        
        # Initialize models
        self.yolo_model = None
        self.clip_model = None
        self.clip_preprocess = None
        self.ocr_reader = None
        self.device = "cuda" if torch and torch.cuda.is_available() and CLIP_AVAILABLE else "cpu"
        
        # Initialize models lazily
        self._models_initialized = False
        
        # Initialize YOLO early for testing
        self._init_yolo()
    
    def _init_yolo(self):
        """Initialize YOLO model"""
        if YOLO_AVAILABLE:
            try:
                self.yolo_model = YOLO('yolov8n.pt')
                logger.info("🚀 YOLOv8 model successfully initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize YOLO: {e}")
                self.yolo_model = None
        else:
            logger.warning("⚠️ YOLO not available (ultralytics not installed)")
            self.yolo_model = None
    
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive image analysis with multiple AI models"""
        try:
            logger.info(f">>> ImageAnalyzer.analyze() called for {file_path}")
            logger.info(f"Starting ImageAnalyzer analysis for {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return {
                    'segments': [],
                    'features': [],
                    'embeddings': [],
                    'metadata': {
                        'error': 'File not found',
                        'analysis_version': '0.1-test',
                        'analyzer': 'simple_test'
                    }
                }
            
            logger.info(f"File validation passed, loading image...")
            
            # Load image
            from PIL import Image
            img = Image.open(file_path)
            width, height = img.size
            
            logger.info(f"🖼️ Image loaded: {width}x{height}, format: {img.format}, mode: {img.mode}")
            
            # Convert to numpy array for analysis
            import numpy as np
            image = np.array(img)
            
            # Comprehensive analysis with all features
            features = []
            success_count = 0
            total_attempts = 0
            
            # 1. Basic technical properties
            features.append({
                'type': 'technical_properties',
                'domain': 'technical',
                'confidence': 1.0,
                'data': {
                    'width': width,
                    'height': height,
                    'format': img.format,
                    'mode': img.mode,
                    'megapixels': round((width * height) / 1_000_000, 2)
                },
                'metadata': {'analyzer': 'basic'}
            })
            success_count += 1
            
            # 2. Extended technical properties
            total_attempts += 1
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                aspect_ratio = width / height
                brightness = np.mean(gray)
                contrast = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                features.append({
                    'type': 'technical_extended',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': {
                        'aspect_ratio': round(aspect_ratio, 3),
                        'brightness': round(brightness, 2),
                        'contrast': round(contrast, 2),
                        'total_pixels': width * height
                    },
                    'metadata': {'analyzer': 'technical_extended'}
                })
                success_count += 1
                logger.info("✅ Technical extended successful")
            except Exception as e:
                logger.error(f"❌ Technical extended error: {e}")
            
            # 3. Comprehensive EXIF
            total_attempts += 1
            try:
                with Image.open(file_path) as exif_img:
                    exif_data = {}
                    if hasattr(exif_img, '_getexif') and exif_img._getexif() is not None:
                        exif = exif_img._getexif()
                        for tag_id, value in exif.items():
                            try:
                                tag = ExifTags.TAGS.get(tag_id, tag_id)
                                exif_data[str(tag)] = str(value)
                            except:
                                exif_data[str(tag_id)] = str(value)
                
                # Extract camera info
                camera_info = {}
                camera_fields = ['Make', 'Model', 'Software', 'DateTime', 'Artist']
                for field in camera_fields:
                    if field in exif_data:
                        camera_info[field] = exif_data[field]
                
                # Extract exposure info  
                exposure_info = {}
                exposure_fields = ['ExposureTime', 'FNumber', 'ISO', 'Flash', 'FocalLength']
                for field in exposure_fields:
                    if field in exif_data:
                        exposure_info[field] = exif_data[field]
                
                features.append({
                    'type': 'exif_comprehensive',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': {
                        'exif_count': len(exif_data),
                        'camera_info': camera_info,
                        'exposure_info': exposure_info,
                        'sample_exif': dict(list(exif_data.items())[:15])
                    },
                    'metadata': {'analyzer': 'exif_comprehensive'}
                })
                success_count += 1
                logger.info(f"✅ EXIF comprehensive successful: {len(exif_data)} tags")
            except Exception as e:
                logger.error(f"❌ EXIF comprehensive error: {e}")
            
            # 4. Color analysis (simplified)
            total_attempts += 1
            try:
                # Simple color statistics instead of KMeans
                hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
                
                # Sample colors efficiently
                step = max(1, (image.shape[0] * image.shape[1]) // 10000)  # Sample ~10k pixels
                sampled_pixels = image[::step, ::step].reshape(-1, 3)
                
                features.append({
                    'type': 'color_analysis',
                    'domain': 'visual',
                    'confidence': 0.9,
                    'data': {
                        'mean_color_rgb': np.mean(sampled_pixels, axis=0).tolist(),
                        'mean_hue': round(np.mean(hsv[:,:,0]), 2),
                        'mean_saturation': round(np.mean(hsv[:,:,1]), 2),
                        'mean_value': round(np.mean(hsv[:,:,2]), 2),
                        'color_variance': np.std(sampled_pixels).tolist()[0] if sampled_pixels.size > 0 else 0
                    },
                    'metadata': {'analyzer': 'color_analysis_simple'}
                })
                success_count += 1
                logger.info("✅ Color analysis successful")
            except Exception as e:
                logger.error(f"❌ Color analysis error: {e}")
            
            # 5. Image quality assessment
            total_attempts += 1
            try:
                # Blur detection
                gray_blur = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                blur_score = cv2.Laplacian(gray_blur, cv2.CV_64F).var()
                
                # Brightness vs noise ratio
                brightness = np.mean(gray_blur)
                noise_level = np.std(gray_blur)
                signal_noise_ratio = brightness / noise_level if noise_level > 0 else 1000
                
                features.append({
                    'type': 'image_quality',
                    'domain': 'technical',
                    'confidence': 0.9,
                    'data': {
                        'blur_score': round(blur_score, 2),
                        'signal_noise_ratio': round(signal_noise_ratio, 2),
                        'brightness': round(brightness, 2),
                        'noise_level': round(signal_noise_ratio, 2),
                        'quality_assessment': 'excellent' if blur_score > 1000 else 'good' if blur_score > 500 else 'fair'
                    },
                    'metadata': {'analyzer': 'image_quality'}
                })
                success_count += 1
                logger.info("✅ Image quality successful")
            except Exception as e:
                logger.error(f"❌ Image quality error: {e}")
            
            # 6. Composition analysis
            total_attempts += 1
            try:
                # Rule of thirds analysis
                rule_of_thirds_lines = [
                    (width // 3, 0, width // 3, height),
                    (2 * width // 3, 0, 2 * width // 3, height),
                    (0, height // 3, width, height // 3),
                    (0, 2 * height // 3, width, 2 * height // 3)
                ]
                
                # Simple symmetry analysis
                left_half = gray[:, :width//2]
                right_half = cv2.flip(gray[:, width//2:], 1)
                min_size = min(left_half.shape[1], right_half.shape[1])
                left_half = left_half[:, :min_size]
                right_half = right_half[:, :min_size]
                symmetry_score = 1.0 - np.mean(np.abs(left_half.astype(float) - right_half.astype(float))) / 255.0
                
                features.append({
                    'type': 'composition',
                    'domain': 'visual',
                    'confidence': 0.8,
                    'data': {
                        'symmetry_score': round(symmetry_score, 3),
                        'aspect_ratio': round(width / height, 3),
                        'rule_of_thirds_possible': True,
                        'image_orientation': 'landscape' if width > height else 'portrait'
                    },
                    'metadata': {'analyzer': 'composition'}
                })
                success_count += 1
                logger.info("✅ Composition successful")
            except Exception as e:
                logger.error(f"❌ Composition error: {e}")
            
            # 6. Object Detection (YOLO) - guaranteed execution with logging
            total_attempts += 1
            try:
                logger.info(f"🔍 Starting YOLO analysis... YOLO_AVAILABLE: {YOLO_AVAILABLE}, yolo_model: {'None' if self.yolo_model is None else 'Initialized'}")
                
                if YOLO_AVAILABLE and self.yolo_model:
                    logger.info("🚀 Running YOLO inference...")
                    # Run YOLO detection directly
                    results = self.yolo_model(file_path)
                    detected_objects = []
                    all_detections = []  # Include all detections regardless of confidence
                    
                    logger.info(f"📊 YOLO returned {len(results)} result(s)")
                    
                    for r in results:
                        if r.boxes is not None and len(r.boxes) > 0:
                            logger.info(f"🔍 Processing {len(r.boxes)} detections...")
                            for i, box in enumerate(r.boxes):
                                confidence = float(box.conf[0])
                                class_id = int(box.cls[0])
                                class_name = self.yolo_model.names[class_id]
                                
                                detection = {
                                    'confidence': confidence,
                                    'class': class_name,
                                    'class_id': class_id,
                                    'bbox': box.xyxy[0].tolist()
                                }
                                all_detections.append(detection)
                                
                                # Only add high confidence detections to final result
                                if confidence > 0.5:
                                    detected_objects.append(detection)
                                    logger.info(f"  ✅ High confidence detection: {class_name} ({confidence:.2f})")
                                else:
                                    logger.info(f"  ⚪ Low confidence detection: {class_name} ({confidence:.2f})")
                        else:
                            logger.info("📭 No boxes found in YOLO result")
                    
                    logger.info(f"🎯 YOLO Analysis Summary:")
                    logger.info(f"  - Total detections: {len(all_detections)}")
                    logger.info(f"  - High confidence (>0.5): {len(detected_objects)}")
                    logger.info(f"  - Classes found: {list(set([d['class'] for d in all_detections]))}")
                    
                    # Always add YOLO feature, even if no objects detected
                    features.append({
                        'type': 'object_detection',
                        'domain': 'visual',
                        'confidence': 0.8,
                        'data': {
                            'objects': detected_objects,
                            'all_detections': all_detections,  # Include all detections
                            'total_count': len(detected_objects),
                            'total_detections': len(all_detections),
                            'detected_classes': list(set([d['class'] for d in all_detections])),
                            'model': 'YOLOv8n',
                            'status': 'completed'
                        },
                        'metadata': {'analyzer': 'yolo_detection'}
                    })
                    success_count += 1
                    logger.info(f"✅ YOLO analysis completed successfully")
                else:
                    logger.warning("⚠️ YOLO not available, adding placeholder feature")
                    features.append({
                        'type': 'object_detection',
                        'domain': 'visual',
                        'confidence': 0.0,
                        'data': {
                            'objects': [],
                            'total_count': 0,
                            'model': 'YOLOv8n',
                            'status': 'unavailable',
                            'error': 'YOLO not available'
                        },
                        'metadata': {'analyzer': 'yolo_detection'}
                    })
                    success_count += 1
                    logger.info("✅ YOLO placeholder added")
            except Exception as e:
                logger.error(f"❌ Object detection error: {e}")
                # Add error feature
                features.append({
                    'type': 'object_detection',
                    'domain': 'visual',
                    'confidence': 0.0,
                    'data': {
                        'objects': [],
                        'total_count': 0,
                        'model': 'YOLOv8n',
                        'status': 'error',
                        'error': str(e)
                    },
                    'metadata': {'analyzer': 'yolo_detection'}
                })
                logger.info("✅ YOLO error feature added")
            
            # 7. Face Analysis (DeepFace) - add safely
            total_attempts += 1
            try:
                # Dynamic check for DeepFace availability
                try:
                    from deepface import DeepFace
                    deepface_available_runtime = True
                    logger.info(f"🧑 Starting DeepFace analysis... DEEPFACE_AVAILABLE: {DEEPFACE_AVAILABLE}, Runtime check: {deepface_available_runtime}")
                except ImportError:
                    deepface_available_runtime = False
                    logger.info(f"🧑 DeepFace runtime check failed: {DEEPFACE_AVAILABLE}")
                
                if deepface_available_runtime:
                    logger.info("🚀 Running DeepFace inference...")
                    
                    # DeepFace analysis (import fresh in runtime)
                    face_analyses = DeepFace.analyze(
                        img_path=file_path,
                        actions=['age', 'gender', 'race', 'emotion'],
                        enforce_detection=False,
                        silent=True
                    )
                    
                    logger.info(f"📊 DeepFace returned {len(face_analyses)} face(s)")
                    
                    # Process results
                    faces = []
                    for i, face in enumerate(face_analyses):
                        face_data = {
                            'face_id': i,
                            'age': face.get('age', 'unknown'),
                            'gender': face.get('dominant_gender', 'unknown'),
                            'race': face.get('dominant_race', 'unknown'),
                            'emotion': face.get('dominant_emotion', 'unknown'),
                            'confidence': {
                                'age': face.get('age', 0),
                                'gender': face.get(f"{face.get('dominant_gender', '')}_confidence", 0),
                                'race': face.get(f"{face.get('dominant_race', '')}_confidence", 0),
                                'emotion': face.get(f"{face.get('dominant_emotion', '')}_confidence", 0)
                            }
                        }
                        faces.append(face_data)
                        logger.info(f"  🧑 Face {i}: {face_data['age']} {face_data['gender']}, emotion: {face_data['emotion']}")
                    
                    features.append({
                        'type': 'face_analysis',
                        'domain': 'visual',
                        'confidence': 0.8,
                        'data': {
                            'faces': faces,
                            'total_faces': len(faces),
                            'model': 'DeepFace',
                            'status': 'completed'
                        },
                        'metadata': {'analyzer': 'deepface'}
                    })
                    success_count += 1
                    logger.info(f"✅ DeepFace analysis completed: {len(faces)} faces detected")
                else:
                    logger.warning("⚠️ DeepFace not available, adding placeholder feature")
                    features.append({
                        'type': 'face_analysis',
                        'domain': 'visual',
                        'confidence': 0.0,
                        'data': {
                            'faces': [],
                            'total_faces': 0,
                            'model': 'DeepFace',
                            'status': 'unavailable',
                            'error': 'DeepFace not available'
                        },
                        'metadata': {'analyzer': 'deepface'}
                    })
                    success_count += 1
                    logger.info("✅ DeepFace placeholder added")
            except Exception as e:
                logger.error(f"❌ Face analysis error: {e}")
                # Add error feature
                features.append({
                    'type': 'face_analysis',
                    'domain': 'visual',
                    'confidence': 0.0,
                    'data': {
                        'faces': [],
                        'total_faces': 0,
                        'model': 'DeepFace',
                        'status': 'error',
                        'error': str(e)
                    },
                    'metadata': {'analyzer': 'deepface'}
                })
                logger.info("✅ DeepFace error feature added")
            
            logger.info(f"🎯 Analysis complete: {success_count}/{total_attempts} analyzers successful!")
            
            # Add basic technical properties as fallback
            if not features:
                features = [
                    {
                        'type': 'technical_properties',
                        'domain': 'technical',
                        'confidence': 1.0,
                        'data': {
                            'width': width,
                            'height': height,
                            'format': img.format,
                            'mode': img.mode,
                            'megapixels': round((width * height) / 1_000_000, 2)
                        },
                        'metadata': {'analyzer': 'basic_fallback'}
                    }
                ]
            
            logger.info(f"✅ Generated {len(features)} features")
            
            # Create result
            result = {
                'segments': [],
                'features': features,
                'embeddings': [],
                'metadata': {
                    'analysis_version': '0.1-test',
                    'analyzer': 'simple_test'
                }
            }
            
            logger.info(f"Completed ImageAnalyzer analysis for {file_path}: {len(result.get('segments', []))} segments, {len(result.get('features', []))} features, {len(result.get('embeddings', []))} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            return {
                'segments': [],
                'features': [],
                'embeddings': [],
                'metadata': {
                    'error': str(e),
                    'analysis_version': '0.1-test',
                    'analyzer': 'simple_test'
                }
            }
    
    async def _initialize_models(self):
        """Initialize AI models asynchronously"""
        try:
            # Initialize YOLO model
            if YOLO_AVAILABLE:
                self.yolo_model = YOLO('yolov8n.pt')
                logger.info("YOLO model initialized")
            
            # Initialize CLIP model
            if CLIP_AVAILABLE:
                self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
                logger.info(f"CLIP model initialized on {self.device}")
            
            # Initialize OCR reader
            if EASYOCR_AVAILABLE:
                self.ocr_reader = easyocr.Reader(['en', 'de'])
                logger.info("EasyOCR reader initialized")
                
        except Exception as e:
            logger.error(f"Model initialization failed: {str(e)}")
    
    async def _load_image(self, file_path: str) -> Optional[np.ndarray]:
        """Load image as numpy array"""
        try:
            image = cv2.imread(file_path)
            if image is not None:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return None
        except Exception as e:
            logger.error(f"Failed to load image: {str(e)}")
            return None
    
    def _get_models_used(self) -> List[str]:
        """Get list of models used in analysis"""
        models = []
        if YOLO_AVAILABLE and self.yolo_model:
            models.append("YOLOv8")
        if CLIP_AVAILABLE and self.clip_model:
            models.append("CLIP")
        if DEEPFACE_AVAILABLE:
            models.append("DeepFace")
        if EASYOCR_AVAILABLE and self.ocr_reader:
            models.append("EasyOCR")
        if OPENAI_AVAILABLE:
            models.append("GPT-4-Vision")
        return models
    
    async def _analyze_technical_properties(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Analyze technical image properties"""
        try:
            height, width = image.shape[:2]
            
            # Calculate image metrics
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Calculate aspect ratio
            aspect_ratio = width / height
            
            features = [{
                'type': 'technical_properties',
                'domain': 'technical',
                'confidence': 1.0,
                'data': {
                    'width': width,
                    'height': height,
                    'aspect_ratio': round(aspect_ratio, 3),
                    'sharpness': round(sharpness, 2),
                    'brightness': round(brightness, 2),
                    'contrast': round(contrast, 2),
                    'total_pixels': width * height
                },
                'metadata': {'analyzer': 'technical_properties'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': [],
                'metadata': {'technical_analysis': 'completed'}
            }
            
        except Exception as e:
            logger.error(f"Technical properties analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _extract_exif_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive EXIF metadata from image"""
        try:
            with Image.open(file_path) as img:
                exif_data = {}
                
                # Standard EXIF data with robust error handling
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        try:
                            tag = ExifTags.TAGS.get(tag_id, tag_id)
                            # Robust string conversion
                            if isinstance(value, (bytes, bytearray)):
                                exif_data[str(tag)] = value.decode('utf-8', errors='ignore')
                            else:
                                exif_data[str(tag)] = str(value)
                        except Exception as tag_error:
                            logger.warning(f"Tag {tag_id} conversion failed: {tag_error}")
                            exif_data[str(tag_id)] = str(value)
                
                # Additional image information
                image_info = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                    'palette': img.palette is not None,
                    'info': dict(img.info) if img.info else {}
                }
                
                # GPS data extraction with robust handling
                gps_data = {}
                try:
                    if 'GPSInfo' in exif_data:
                        gps_info = exif_data['GPSInfo']
                        if isinstance(gps_info, str):
                            gps_data['raw'] = gps_info
                            # Try to extract GPS coordinates from string representation
                            import re
                            coords = re.findall(r'[-+]?\d*\.?\d+', gps_info)
                            if len(coords) >= 2:
                                gps_data['latitude'] = coords[0]
                                gps_data['longitude'] = coords[1]
                        else:
                            gps_data = gps_info if isinstance(gps_info, dict) else {'raw': str(gps_info)}
                except Exception as gps_e:
                    logger.warning(f"GPS data parsing failed: {gps_e}")
                    gps_data['error'] = str(gps_e)
                
                # Camera information extraction
                camera_info = {}
                camera_fields = [
                    'Make', 'Model', 'Software', 'DateTime', 'DateTimeOriginal', 
                    'DateTimeDigitized', 'Artist', 'Copyright', 'ImageDescription',
                    'Orientation', 'XResolution', 'YResolution', 'ResolutionUnit'
                ]
                
                for field in camera_fields:
                    try:
                        if field in exif_data:
                            camera_info[field] = exif_data[field]
                    except Exception as field_error:
                        logger.warning(f"Camera field {field} extraction failed: {field_error}")
                
                # Exposure settings extraction
                exposure_info = {}
                exposure_fields = [
                    'ExposureTime', 'FNumber', 'ISO', 'Flash', 'FocalLength',
                    'ExposureMode', 'WhiteBalance', 'DigitalZoomRatio', 'SceneCaptureType'
                ]
                
                for field in exposure_fields:
                    try:
                        if field in exif_data:
                            exposure_info[field] = exif_data[field]
                    except Exception as field_error:
                        logger.warning(f"Exposure field {field} extraction failed: {field_error}")
                
                # Create comprehensive EXIF feature with all data
                comprehensive_exif = {
                    'standard_exif': exif_data,
                    'image_info': image_info,
                    'gps_data': gps_data,
                    'camera_info': camera_info,
                    'exposure_info': exposure_info,
                    'exif_count': len(exif_data),
                    'has_gps': bool(gps_data and 'latitude' in gps_data),
                    'has_camera_info': bool(camera_info),
                    'has_exposure_info': bool(exposure_info)
                }
                
                features = [{
                    'type': 'exif_metadata',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': comprehensive_exif,
                    'metadata': {
                        'analyzer': 'comprehensive_exif_extraction',
                        'exif_fields_count': len(exif_data),
                        'has_gps': bool(gps_data and 'latitude' in gps_data),
                        'has_camera_data': bool(camera_info),
                        'has_exposure_data': bool(exposure_info)
                    }
                }]
                
                return {
                    'segments': [],
                    'features': features,
                    'embeddings': []
                }
                
        except Exception as e:
            logger.error(f"EXIF extraction failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _analyze_image_quality(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image quality metrics"""
        try:
            height, width = image.shape[:2]
            
            # Convert to grayscale for quality analysis
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Sharpness analysis using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 1000, 1.0)  # Normalize to 0-1
            
            # Noise analysis using standard deviation
            noise_level = np.std(gray)
            noise_score = min(noise_level / 50, 1.0)  # Normalize to 0-1
            
            # Blur detection using gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            blur_score = 1.0 - min(np.mean(gradient_magnitude) / 100, 1.0)
            
            # Compression artifacts detection
            # High frequency content analysis
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)
            
            # Calculate high frequency energy
            h, w = magnitude_spectrum.shape
            center_h, center_w = h // 2, w // 2
            high_freq_region = magnitude_spectrum[
                center_h - h//4:center_h + h//4,
                center_w - w//4:center_w + w//4
            ]
            high_freq_energy = np.mean(high_freq_region)
            
            # Overall quality score
            quality_score = (sharpness_score + (1 - noise_score) + (1 - blur_score)) / 3
            
            quality_data = {
                'sharpness_score': round(sharpness_score, 4),
                'noise_level': round(noise_level, 2),
                'noise_score': round(noise_score, 4),
                'blur_score': round(blur_score, 4),
                'high_frequency_energy': round(high_freq_energy, 4),
                'overall_quality_score': round(quality_score, 4),
                'quality_assessment': self._assess_quality(quality_score),
                'recommendations': self._get_quality_recommendations(sharpness_score, noise_score, blur_score)
            }
            
            features = [{
                'type': 'image_quality',
                'domain': 'technical',
                'confidence': 0.9,
                'data': quality_data,
                'metadata': {'analyzer': 'quality_analysis'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Image quality analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    def _assess_quality(self, quality_score: float) -> str:
        """Assess overall image quality"""
        if quality_score >= 0.8:
            return "excellent"
        elif quality_score >= 0.6:
            return "good"
        elif quality_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _get_quality_recommendations(self, sharpness: float, noise: float, blur: float) -> List[str]:
        """Get quality improvement recommendations"""
        recommendations = []
        
        if sharpness < 0.3:
            recommendations.append("Image appears soft - consider sharpening")
        if noise > 0.7:
            recommendations.append("High noise level detected - consider noise reduction")
        if blur > 0.6:
            recommendations.append("Image appears blurred - check focus or camera stability")
        
        if not recommendations:
            recommendations.append("Image quality is good")
            
        return recommendations
    
    async def _analyze_lighting_conditions(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Analyze lighting conditions and exposure"""
        try:
            # Convert to LAB color space for better lighting analysis
            if len(image.shape) == 3:
                lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
                l_channel = lab[:, :, 0]  # Luminance channel
            else:
                l_channel = image
            
            # Calculate lighting metrics
            mean_brightness = np.mean(l_channel)
            brightness_std = np.std(l_channel)
            
            # Histogram analysis
            hist = cv2.calcHist([l_channel], [0], None, [256], [0, 256])
            hist = hist.flatten()
            
            # Find peaks in histogram
            if SCIPY_AVAILABLE:
                peaks, _ = find_peaks(hist, height=np.max(hist) * 0.1)
            else:
                peaks = []
            
            # Analyze histogram distribution
            total_pixels = np.sum(hist)
            dark_pixels = np.sum(hist[:85]) / total_pixels  # 0-85 (dark)
            mid_pixels = np.sum(hist[85:170]) / total_pixels  # 85-170 (mid)
            bright_pixels = np.sum(hist[170:]) / total_pixels  # 170-255 (bright)
            
            # Shadow and highlight analysis
            shadow_threshold = 30
            highlight_threshold = 225
            shadow_pixels = np.sum(l_channel < shadow_threshold)
            highlight_pixels = np.sum(l_channel > highlight_threshold)
            shadow_ratio = shadow_pixels / l_channel.size
            highlight_ratio = highlight_pixels / l_channel.size
            
            # Dynamic range analysis
            min_val = np.min(l_channel)
            max_val = np.max(l_channel)
            dynamic_range = max_val - min_val
            
            # Lighting assessment
            lighting_assessment = self._assess_lighting(
                mean_brightness, brightness_std, shadow_ratio, highlight_ratio, dynamic_range
            )
            
            lighting_data = {
                'mean_brightness': round(mean_brightness, 2),
                'brightness_std': round(brightness_std, 2),
                'dynamic_range': round(dynamic_range, 2),
                'histogram_distribution': {
                    'dark_pixels_ratio': round(dark_pixels, 4),
                    'mid_pixels_ratio': round(mid_pixels, 4),
                    'bright_pixels_ratio': round(bright_pixels, 4)
                },
                'shadow_analysis': {
                    'shadow_ratio': round(shadow_ratio, 4),
                    'shadow_pixels': int(shadow_pixels)
                },
                'highlight_analysis': {
                    'highlight_ratio': round(highlight_ratio, 4),
                    'highlight_pixels': int(highlight_pixels)
                },
                'lighting_assessment': lighting_assessment,
                'exposure_recommendations': self._get_exposure_recommendations(
                    mean_brightness, shadow_ratio, highlight_ratio
                )
            }
            
            features = [{
                'type': 'lighting_analysis',
                'domain': 'technical',
                'confidence': 0.9,
                'data': lighting_data,
                'metadata': {'analyzer': 'lighting_analysis'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Lighting analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    def _assess_lighting(self, brightness: float, std: float, shadow_ratio: float, 
                        highlight_ratio: float, dynamic_range: float) -> str:
        """Assess lighting conditions"""
        if 100 <= brightness <= 155 and std > 30 and dynamic_range > 100:
            return "well_exposed"
        elif brightness < 100:
            return "underexposed"
        elif brightness > 155:
            return "overexposed"
        elif shadow_ratio > 0.3:
            return "heavy_shadows"
        elif highlight_ratio > 0.3:
            return "blown_highlights"
        else:
            return "mixed_lighting"
    
    def _get_exposure_recommendations(self, brightness: float, shadow_ratio: float, 
                                    highlight_ratio: float) -> List[str]:
        """Get exposure improvement recommendations"""
        recommendations = []
        
        if brightness < 100:
            recommendations.append("Image appears underexposed - increase exposure")
        elif brightness > 155:
            recommendations.append("Image appears overexposed - decrease exposure")
        
        if shadow_ratio > 0.3:
            recommendations.append("Heavy shadows detected - consider fill light or shadow recovery")
        
        if highlight_ratio > 0.3:
            recommendations.append("Blown highlights detected - consider highlight recovery")
        
        if not recommendations:
            recommendations.append("Exposure looks good")
            
        return recommendations
    
    async def _analyze_image_authenticity(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image authenticity and potential manipulation"""
        try:
            # Convert to grayscale for analysis
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Error Level Analysis (ELA) for compression artifacts
            # This is a simplified version - real ELA requires multiple JPEG compressions
            quality_95 = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])[1]
            quality_75 = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 75])[1]
            
            # Load back and compare
            img_95 = cv2.imdecode(quality_95, cv2.IMREAD_GRAYSCALE)
            img_75 = cv2.imdecode(quality_75, cv2.IMREAD_GRAYSCALE)
            
            # Calculate difference
            diff_95 = cv2.absdiff(gray, img_95)
            diff_75 = cv2.absdiff(gray, img_75)
            
            # Analyze differences
            mean_diff_95 = np.mean(diff_95)
            mean_diff_75 = np.mean(diff_75)
            std_diff_95 = np.std(diff_95)
            std_diff_75 = np.std(diff_75)
            
            # Edge consistency analysis
            edges_original = cv2.Canny(gray, 50, 150)
            edges_95 = cv2.Canny(img_95, 50, 150)
            edges_75 = cv2.Canny(img_75, 50, 150)
            
            edge_consistency_95 = np.sum(edges_original == edges_95) / edges_original.size
            edge_consistency_75 = np.sum(edges_original == edges_75) / edges_original.size
            
            # Noise pattern analysis
            # High frequency noise should be consistent in natural images
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.abs(f_shift)
            
            # Analyze noise patterns
            h, w = magnitude_spectrum.shape
            center_h, center_w = h // 2, w // 2
            
            # Check for regular patterns that might indicate manipulation
            # This is a simplified check
            noise_consistency = np.std(magnitude_spectrum[center_h-50:center_h+50, center_w-50:center_w+50])
            
            # Authenticity assessment
            authenticity_score = self._calculate_authenticity_score(
                mean_diff_95, mean_diff_75, edge_consistency_95, edge_consistency_75, noise_consistency
            )
            
            authenticity_data = {
                'compression_analysis': {
                    'mean_diff_95': round(mean_diff_95, 4),
                    'mean_diff_75': round(mean_diff_75, 4),
                    'std_diff_95': round(std_diff_95, 4),
                    'std_diff_75': round(std_diff_75, 4)
                },
                'edge_consistency': {
                    'consistency_95': round(edge_consistency_95, 4),
                    'consistency_75': round(edge_consistency_75, 4)
                },
                'noise_analysis': {
                    'noise_consistency': round(noise_consistency, 4)
                },
                'authenticity_score': round(authenticity_score, 4),
                'authenticity_assessment': self._assess_authenticity(authenticity_score),
                'manipulation_indicators': self._get_manipulation_indicators(
                    mean_diff_95, edge_consistency_95, noise_consistency
                )
            }
            
            features = [{
                'type': 'authenticity_analysis',
                'domain': 'forensic',
                'confidence': 0.7,  # Lower confidence as this is complex
                'data': authenticity_data,
                'metadata': {'analyzer': 'authenticity_analysis'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Authenticity analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    def _calculate_authenticity_score(self, diff_95: float, diff_75: float, 
                                    edge_95: float, edge_75: float, noise: float) -> float:
        """Calculate authenticity score (0-1, higher is more authentic)"""
        # Normalize metrics
        diff_score = 1.0 - min((diff_95 + diff_75) / 100, 1.0)
        edge_score = (edge_95 + edge_75) / 2
        noise_score = 1.0 - min(noise / 1000, 1.0)
        
        # Weighted combination
        authenticity_score = (diff_score * 0.4 + edge_score * 0.4 + noise_score * 0.2)
        return max(0, min(1, authenticity_score))
    
    def _assess_authenticity(self, score: float) -> str:
        """Assess image authenticity"""
        if score >= 0.8:
            return "likely_authentic"
        elif score >= 0.6:
            return "probably_authentic"
        elif score >= 0.4:
            return "uncertain"
        else:
            return "suspicious"
    
    def _get_manipulation_indicators(self, diff: float, edge_consistency: float, 
                                   noise_consistency: float) -> List[str]:
        """Get potential manipulation indicators"""
        indicators = []
        
        if diff > 20:
            indicators.append("Unusual compression artifacts")
        if edge_consistency < 0.7:
            indicators.append("Inconsistent edge patterns")
        if noise_consistency > 500:
            indicators.append("Irregular noise patterns")
        
        if not indicators:
            indicators.append("No obvious manipulation indicators")
            
        return indicators
    
    async def _detect_objects_yolo(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Detect objects using YOLO v8"""
        try:
            if not YOLO_AVAILABLE or self.yolo_model is None:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            # Run YOLO detection
            results = self.yolo_model(file_path)
            
            detected_objects = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0])
                        class_id = int(box.cls[0])
                        class_name = self.yolo_model.names[class_id]
                        
                        detected_objects.append({
                            'class': class_name,
                            'confidence': round(confidence, 3),
                            'bbox': [int(x1), int(y1), int(x2-x1), int(y2-y1)],
                            'class_id': class_id
                        })
            
            # Create features
            features = []
            if detected_objects:
                # Group objects by class
                object_counts = {}
                for obj in detected_objects:
                    class_name = obj['class']
                    object_counts[class_name] = object_counts.get(class_name, 0) + 1
                
                features.append({
                    'type': 'object_detection',
                    'domain': 'visual',
                    'confidence': 0.9,
                    'data': {
                        'objects': detected_objects,
                        'total_count': len(detected_objects),
                        'class_counts': object_counts,
                        'model': 'YOLOv8'
                    },
                    'metadata': {'analyzer': 'yolo_detection'}
                })
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"YOLO object detection failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _analyze_faces_deepface(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Analyze faces using DeepFace"""
        try:
            if not DEEPFACE_AVAILABLE:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            # Analyze faces
            face_analyses = DeepFace.analyze(
                img_path=file_path,
                actions=['age', 'gender', 'race', 'emotion'],
                enforce_detection=False
            )
            
            features = []
            if face_analyses:
                # Handle single face or multiple faces
                if not isinstance(face_analyses, list):
                    face_analyses = [face_analyses]
                
                for i, face in enumerate(face_analyses):
                    if 'region' in face:
                        features.append({
                            'type': 'face_analysis',
                            'domain': 'visual',
                            'confidence': face.get('confidence', 0.8),
                            'data': {
                                'face_id': i,
                                'age': face.get('age'),
                                'gender': face.get('dominant_gender'),
                                'race': face.get('dominant_race'),
                                'emotion': face.get('dominant_emotion'),
                                'region': face.get('region'),
                                'emotions': face.get('emotion', {}),
                                'gender_confidence': face.get('gender', {}),
                                'race_confidence': face.get('race', {})
                            },
                            'metadata': {'analyzer': 'deepface'}
                        })
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"DeepFace analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _extract_color_analysis(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Comprehensive color analysis"""
        try:
            # Reshape image to be a list of pixels
            pixels = image.reshape(-1, 3)
            
            # Sample pixels for performance (max 10000 pixels)
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]
            
            # Calculate dominant colors using k-means
            kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
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
                frequency = color_counts[i] / len(labels)
                # Convert RGB to hex
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                
                dominant_colors.append({
                    'rgb': color.tolist(),
                    'hex': hex_color,
                    'frequency': round(frequency, 3)
                })
            
            # Sort by frequency
            dominant_colors.sort(key=lambda x: x['frequency'], reverse=True)
            
            # Calculate color statistics
            mean_color = np.mean(pixels, axis=0).astype(int)
            color_variance = np.var(pixels, axis=0)
            
            features = [{
                'type': 'color_analysis',
                'domain': 'visual',
                'confidence': 0.9,
                'data': {
                    'dominant_colors': dominant_colors[:5],  # Top 5 colors
                    'mean_color': mean_color.tolist(),
                    'color_variance': color_variance.tolist(),
                    'total_colors': len(dominant_colors),
                    'brightness': float(np.mean(pixels)),
                    'saturation': float(np.mean(np.std(pixels, axis=1)))
                },
                'metadata': {'analyzer': 'color_analysis'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Color analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _analyze_scene_composition(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Analyze scene composition and layout"""
        try:
            height, width = image.shape[:2]
            
            # Basic composition analysis
            center_x, center_y = width // 2, height // 2
            
            # Rule of thirds analysis
            rule_of_thirds_x = [width // 3, 2 * width // 3]
            rule_of_thirds_y = [height // 3, 2 * height // 3]
            
            # Edge detection for composition
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Calculate edge density in different regions
            regions = {
                'top_left': edges[:height//2, :width//2],
                'top_right': edges[:height//2, width//2:],
                'bottom_left': edges[height//2:, :width//2],
                'bottom_right': edges[height//2:, width//2:]
            }
            
            region_densities = {}
            for region_name, region in regions.items():
                density = np.sum(region > 0) / region.size
                region_densities[region_name] = round(density, 3)
            
            features = [{
                'type': 'scene_composition',
                'domain': 'visual',
                'confidence': 0.8,
                'data': {
                    'aspect_ratio': round(width / height, 3),
                    'orientation': 'landscape' if width > height else 'portrait' if height > width else 'square',
                    'center_point': [center_x, center_y],
                    'rule_of_thirds': {
                        'x_lines': rule_of_thirds_x,
                        'y_lines': rule_of_thirds_y
                    },
                    'edge_density_by_region': region_densities,
                    'overall_edge_density': round(np.sum(edges > 0) / edges.size, 3)
                },
                'metadata': {'analyzer': 'scene_composition'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Scene composition analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _detect_text_ocr(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Detect text in image using OCR"""
        try:
            if not EASYOCR_AVAILABLE or self.ocr_reader is None:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            # Run OCR
            results = self.ocr_reader.readtext(file_path)
            
            text_regions = []
            all_text = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Filter low confidence results
                    text_regions.append({
                        'text': text,
                        'confidence': round(confidence, 3),
                        'bbox': bbox,
                        'language': 'auto'  # EasyOCR auto-detects language
                    })
                    all_text.append(text)
            
            features = []
            if text_regions:
                features.append({
                    'type': 'text_detection',
                    'domain': 'text',
                    'confidence': 0.8,
                    'data': {
                        'has_text': True,
                        'text_regions': text_regions,
                        'total_text': ' '.join(all_text),
                        'text_count': len(text_regions),
                        'languages_detected': ['en', 'de']  # Based on reader initialization
                    },
                    'metadata': {'analyzer': 'easyocr'}
                })
            else:
                features.append({
                    'type': 'text_detection',
                    'domain': 'text',
                    'confidence': 0.9,
                    'data': {
                        'has_text': False,
                        'text_regions': [],
                        'total_text': '',
                        'text_count': 0
                    },
                    'metadata': {'analyzer': 'easyocr'}
                })
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"OCR text detection failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _generate_semantic_description(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Generate semantic description using GPT-4 Vision"""
        try:
            if not OPENAI_AVAILABLE:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            # Convert image to base64
            pil_image = Image.fromarray(image)
            buffer = BytesIO()
            pil_image.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Prepare OpenAI API call
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in detail. Include: 1) Main objects and people, 2) Scene setting and environment, 3) Colors and lighting, 4) Mood and atmosphere, 5) Any text visible, 6) Overall composition. Provide a detailed description in 2-3 sentences, then extract 10-15 relevant keywords/tags."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            description = response.choices[0].message.content
            
            # Extract keywords (simple approach)
            keywords = []
            if description:
                # Simple keyword extraction
                words = description.lower().split()
                # Filter common words and extract meaningful terms
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
                keywords = [word.strip('.,!?;:') for word in words if len(word) > 3 and word not in stop_words][:15]
            
            features = [{
                'type': 'semantic_description',
                'domain': 'semantic',
                'confidence': 0.9,
                'data': {
                    'description': description,
                    'keywords': keywords,
                    'model': 'GPT-4-Vision'
                },
                'metadata': {'analyzer': 'gpt4_vision'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Semantic description generation failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _generate_embeddings(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Generate embeddings using CLIP"""
        try:
            if not CLIP_AVAILABLE or self.clip_model is None:
                return {'segments': [], 'features': [], 'embeddings': []}
            
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)
            
            # Preprocess image for CLIP
            image_input = self.clip_preprocess(pil_image).unsqueeze(0).to(self.device)
            
            # Generate image embedding
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                embedding = image_features.cpu().numpy().flatten().tolist()
            
            embeddings = [{
                'type': 'clip_embedding',
                'model': 'CLIP-ViT-B/32',
                'dimensions': len(embedding),
                'embedding': embedding,
                'metadata': {
                    'analyzer': 'clip',
                    'device': self.device
                }
            }]
            
            return {
                'segments': [],
                'features': [],
                'embeddings': embeddings
            }
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _perform_safety_checks(self, file_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Perform safety and content checks"""
        try:
            # Basic safety checks
            height, width = image.shape[:2]
            
            # Check for potential NSFW content (basic heuristics)
            # This is a placeholder - in production, use dedicated NSFW detection models
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Calculate skin tone regions (very basic)
            # Convert to HSV for better skin detection
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            
            # Define skin color range in HSV
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            
            # Create mask for skin regions
            skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_pixels = np.sum(skin_mask > 0)
            skin_ratio = skin_pixels / (height * width)
            
            # Basic content assessment
            features = [{
                'type': 'safety_assessment',
                'domain': 'safety',
                'confidence': 0.7,
                'data': {
                    'nsfw_score': 0.0,  # Placeholder - would use dedicated model
                    'skin_ratio': round(skin_ratio, 3),
                    'content_flags': [],
                    'safety_level': 'safe' if skin_ratio < 0.3 else 'review_recommended',
                    'assessment_method': 'basic_heuristics'
                },
                'metadata': {'analyzer': 'safety_checks'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Safety checks failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
