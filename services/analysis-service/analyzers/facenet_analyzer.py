"""
FaceNet Analyzer for DataFlux Analysis Service
Implements FaceNet-based face recognition and analysis as complement to DeepFace
"""

import asyncio
import logging
import json
import os
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import base64
from io import BytesIO

# FaceNet imports
try:
    from facenet_pytorch import MTCNN, InceptionResnetV1
    import torch
    FACENET_AVAILABLE = True
except ImportError:
    FACENET_AVAILABLE = False
    torch = None

try:
    from .base import BaseAnalyzer
except ImportError:
    # Fallback for direct import
    class BaseAnalyzer:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class FaceNetAnalyzer(BaseAnalyzer):
    """FaceNet-based face recognition and analysis analyzer"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/bmp', 'image/tiff', 'image/webp'
        ]
        
        # Initialize FaceNet models
        self.mtcnn = None
        self.facenet_model = None
        # FaceNet/MTCNN have issues with MPS adaptive pooling, use CPU for now
        # (Future: When PyTorch MPS matures, can switch back to MPS)
        if torch and FACENET_AVAILABLE:
            if torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
                logger.info("🖥️ FaceNet using CPU (MPS has compatibility issues with MTCNN)")
        else:
            self.device = "cpu"
        
        # Face database for recognition (in production, this would be in a proper database)
        self.face_database = {}  # face_id -> face_info
        self.face_embeddings = {}  # face_id -> embedding
        self.face_database_file = "/tmp/dataflux_face_database.json"
        
        # Load existing face database
        self._load_face_database()
        
        # Initialize models lazily
        self._models_initialized = False
        
        logger.info(f"FaceNetAnalyzer initialized on device: {self.device}")
    
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive FaceNet-based face analysis"""
        try:
            logger.info(f"🧑 FaceNetAnalyzer.analyze() called for {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return {
                    'segments': [],
                    'features': [],
                    'embeddings': [],
                    'metadata': {
                        'error': 'File not found',
                        'analysis_version': '1.0-facenet',
                        'analyzer': 'facenet'
                    }
                }
            
            # Initialize models if not done yet
            if not self._models_initialized:
                await self._initialize_models()
            
            # Load image
            image = await self._load_image(file_path)
            if image is None:
                logger.error(f"Failed to load image: {file_path}")
                return {
                    'segments': [],
                    'features': [],
                    'embeddings': [],
                    'metadata': {
                        'error': 'Failed to load image',
                        'analysis_version': '1.0-facenet',
                        'analyzer': 'facenet'
                    }
                }
            
            logger.info(f"🖼️ Image loaded: {image.shape}")
            
            # Resize image for MPS compatibility (dimensions must be divisible by 8)
            # Also limit max size for performance
            max_dimension = 1920  # Good balance for face detection
            height, width = image.shape[:2]
            
            if height > max_dimension or width > max_dimension:
                logger.info(f"🔄 Resizing image from {width}x{height} for MPS compatibility...")
                
                # Calculate new dimensions maintaining aspect ratio
                if height > width:
                    new_height = max_dimension
                    new_width = int((width * max_dimension) / height)
                else:
                    new_width = max_dimension
                    new_height = int((height * max_dimension) / width)
                
                # Ensure dimensions are divisible by 8 for MPS
                new_width = (new_width // 8) * 8
                new_height = (new_height // 8) * 8
                
                # Resize image
                import cv2
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.info(f"✅ Image resized to {new_width}x{new_height} (MPS-compatible)")
            else:
                # Still ensure dimensions are divisible by 8
                new_width = (width // 8) * 8
                new_height = (height // 8) * 8
                
                if new_width != width or new_height != height:
                    logger.info(f"🔄 Adjusting image dimensions to be MPS-compatible...")
                    import cv2
                    image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                    logger.info(f"✅ Image adjusted to {new_width}x{new_height}")
            
            logger.info(f"🖼️ Final image size for FaceNet: {image.shape}")
            
            features = []
            embeddings = []
            
            # 1. Face Detection using MTCNN
            total_attempts = 0
            success_count = 0
            
            total_attempts += 1
            try:
                logger.info("🔍 Starting MTCNN face detection...")
                
                if FACENET_AVAILABLE and self.mtcnn:
                    # Convert numpy array to PIL Image
                    pil_image = Image.fromarray(image)
                    
                    # Detect faces and landmarks
                    boxes, probs, landmarks = self.mtcnn.detect(pil_image, landmarks=True)
                    
                    logger.info(f"📊 MTCNN detected {len(boxes) if boxes is not None else 0} faces")
                    
                    detected_faces = []
                    if boxes is not None and len(boxes) > 0:
                        for i, (box, prob, landmark) in enumerate(zip(boxes, probs, landmarks)):
                            face_data = {
                                'face_id': i,
                                'bbox': box.tolist(),
                                'confidence': float(prob),
                                'landmarks': landmark.tolist() if landmark is not None else [],
                                'face_size': {
                                    'width': float(box[2] - box[0]),
                                    'height': float(box[3] - box[1]),
                                    'area': float((box[2] - box[0]) * (box[3] - box[1]))
                                }
                            }
                            detected_faces.append(face_data)
                            logger.info(f"  🧑 Face {i}: confidence={prob:.3f}, size={face_data['face_size']['width']:.1f}x{face_data['face_size']['height']:.1f}")
                    
                    features.append({
                        'type': 'face_detection',
                        'domain': 'visual',
                        'confidence': 0.9,
                        'data': {
                            'faces': detected_faces,
                            'total_faces': len(detected_faces),
                            'model': 'MTCNN',
                            'detection_method': 'FaceNet-MTCNN',
                            'status': 'completed'
                        },
                        'metadata': {'analyzer': 'facenet_mtcnn'}
                    })
                    success_count += 1
                    logger.info(f"✅ MTCNN face detection completed: {len(detected_faces)} faces")
                else:
                    logger.warning("⚠️ MTCNN not available, adding placeholder feature")
                    features.append({
                        'type': 'face_detection',
                        'domain': 'visual',
                        'confidence': 0.0,
                        'data': {
                            'faces': [],
                            'total_faces': 0,
                            'model': 'MTCNN',
                            'status': 'unavailable',
                            'error': 'MTCNN not available'
                        },
                        'metadata': {'analyzer': 'facenet_mtcnn'}
                    })
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ MTCNN face detection error: {e}")
                features.append({
                    'type': 'face_detection',
                    'domain': 'visual',
                    'confidence': 0.0,
                    'data': {
                        'faces': [],
                        'total_faces': 0,
                        'model': 'MTCNN',
                        'status': 'error',
                        'error': str(e)
                    },
                    'metadata': {'analyzer': 'facenet_mtcnn'}
                })
                success_count += 1
            
            # 2. Face Recognition using FaceNet embeddings
            total_attempts += 1
            try:
                logger.info("🔍 Starting FaceNet face recognition...")
                
                if FACENET_AVAILABLE and self.mtcnn and self.facenet_model:
                    # Convert numpy array to PIL Image
                    pil_image = Image.fromarray(image)
                    
                    # Extract face crops and embeddings
                    face_crops = self.mtcnn(pil_image)
                    
                    if face_crops is not None:
                        # Ensure face_crops is a list/batch (4D tensor)
                        if len(face_crops.shape) == 3:
                            # Single face, add batch dimension
                            face_crops = face_crops.unsqueeze(0)
                        
                        logger.info(f"📊 Processing {len(face_crops)} face crops for recognition...")
                        
                        # Generate embeddings for each face
                        face_crops = face_crops.to(self.device)
                        with torch.no_grad():
                            face_embeddings = self.facenet_model(face_crops)
                        
                        recognized_faces = []
                        for i, embedding in enumerate(face_embeddings):
                            # Normalize embedding
                            embedding_norm = embedding / torch.norm(embedding)
                            
                            # Store embedding for future recognition
                            embedding_key = f"face_{i}_{hash(str(embedding_norm.cpu().numpy()))}"
                            # Don't overwrite existing embeddings here - let _find_best_match_enhanced handle it
                            
                            # Try to match with known faces using enhanced matching
                            best_match = await self._find_best_match_enhanced(embedding_norm)
                            
                            # Create avatar for new faces
                            avatar_filename = None
                            if best_match['is_new_face']:
                                avatar_filename = self._create_face_avatar(face_crops[i], best_match['face_id'])
                                if avatar_filename:
                                    # Update face database with avatar filename
                                    if best_match['face_id'] in self.face_database:
                                        self.face_database[best_match['face_id']]['avatar_filename'] = avatar_filename
                                        self._save_face_database()
                            
                            # Get avatar filename for known faces
                            if not best_match['is_new_face'] and best_match['face_id'] in self.face_database:
                                avatar_filename = self.face_database[best_match['face_id']].get('avatar_filename')
                            
                            face_recognition_data = {
                                'face_id': best_match['face_id'],
                                'face_index': i,
                                'embedding_dimensions': len(embedding_norm),
                                'embedding_key': embedding_key,
                                'best_match': best_match,
                                'is_known_face': not best_match['is_new_face'],
                                'is_new_face': best_match['is_new_face'],
                                'face_quality': self._assess_face_quality(embedding_norm),
                                'identity': best_match['identity'],
                                'confidence': best_match['confidence'],
                                'appearance_count': best_match.get('appearance_count', 1),
                                'first_seen': best_match.get('first_seen'),
                                'last_seen': best_match.get('last_seen'),
                                'avatar_filename': avatar_filename,
                                'avatar_base64': self._get_avatar_base64(avatar_filename) if avatar_filename else None
                            }
                            recognized_faces.append(face_recognition_data)
                            
                            logger.info(f"  🧑 Face {i}: {face_recognition_data['identity']} ({'Known' if face_recognition_data['is_known_face'] else 'New'}), confidence: {face_recognition_data['confidence']:.3f}, quality: {face_recognition_data['face_quality']}")
                        
                        # Create one feature per recognized face
                        for i, face_data in enumerate(recognized_faces):
                            features.append({
                                'type': 'face_recognition',
                                'domain': 'visual',
                                'confidence': face_data['confidence'],
                                'data': {
                                    'face_id': face_data['face_id'],
                                    'face_index': face_data['face_index'],
                                    'identity': face_data['identity'],
                                    'is_known_face': face_data['is_known_face'],
                                    'is_new_face': face_data['is_new_face'],
                                    'confidence': face_data['confidence'],
                                    'appearance_count': face_data['appearance_count'],
                                    'first_seen': face_data['first_seen'],
                                    'last_seen': face_data['last_seen'],
                                    'face_quality': face_data['face_quality'],
                                    'embedding_dimensions': face_data['embedding_dimensions'],
                                    'embedding_key': face_data['embedding_key'],
                                    'avatar_filename': face_data['avatar_filename'],
                                    'avatar_base64': face_data['avatar_base64'],
                                    'recognition_method': 'FaceNet-InceptionResnetV1',
                                    'status': 'completed'
                                },
                                'metadata': {'analyzer': 'facenet_recognition'}
                            })
                        
                        # Add embeddings to result
                        embeddings.extend([{
                            'type': 'facenet_embedding',
                            'model': 'FaceNet-InceptionResnetV1',
                            'dimensions': len(embedding_norm),
                            'embedding': embedding_norm.cpu().numpy().tolist(),
                            'face_id': i,
                            'metadata': {
                                'analyzer': 'facenet',
                                'device': self.device,
                                'embedding_key': embedding_key
                            }
                        } for i, embedding_norm in enumerate(face_embeddings)])
                        
                        success_count += 1
                        logger.info(f"✅ FaceNet recognition completed: {len(recognized_faces)} faces processed (created {len(recognized_faces)} features)")
                    else:
                        logger.info("📭 No faces detected for recognition")
                        features.append({
                            'type': 'face_recognition',
                            'domain': 'visual',
                            'confidence': 0.9,
                            'data': {
                                'recognized_faces': [],
                                'total_faces': 0,
                                'known_faces': 0,
                                'unknown_faces': 0,
                                'model': 'FaceNet-InceptionResnetV1',
                                'status': 'no_faces_detected'
                            },
                            'metadata': {'analyzer': 'facenet_recognition'}
                        })
                        success_count += 1
                else:
                    logger.warning("⚠️ FaceNet not available, adding placeholder feature")
                    features.append({
                        'type': 'face_recognition',
                        'domain': 'visual',
                        'confidence': 0.0,
                        'data': {
                            'recognized_faces': [],
                            'total_faces': 0,
                            'model': 'FaceNet-InceptionResnetV1',
                            'status': 'unavailable',
                            'error': 'FaceNet not available'
                        },
                        'metadata': {'analyzer': 'facenet_recognition'}
                    })
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ FaceNet recognition error: {e}")
                features.append({
                    'type': 'face_recognition',
                    'domain': 'visual',
                    'confidence': 0.0,
                    'data': {
                        'recognized_faces': [],
                        'total_faces': 0,
                        'model': 'FaceNet-InceptionResnetV1',
                        'status': 'error',
                        'error': str(e)
                    },
                    'metadata': {'analyzer': 'facenet_recognition'}
                })
                success_count += 1
            
            # 3. Face Quality Assessment
            total_attempts += 1
            try:
                logger.info("🔍 Starting face quality assessment...")
                
                if FACENET_AVAILABLE and self.mtcnn:
                    pil_image = Image.fromarray(image)
                    boxes, probs, landmarks = self.mtcnn.detect(pil_image, landmarks=True)
                    
                    quality_assessments = []
                    if boxes is not None and len(boxes) > 0:
                        for i, (box, prob, landmark) in enumerate(zip(boxes, probs, landmarks)):
                            quality_data = {
                                'face_id': i,
                                'detection_confidence': float(prob),
                                'face_size_score': self._calculate_size_score(box),
                                'face_angle_score': self._calculate_angle_score(landmark) if landmark is not None else 0.5,
                                'face_illumination_score': self._calculate_illumination_score(image, box),
                                'overall_quality_score': 0.0,  # Will be calculated
                                'quality_assessment': 'unknown'  # Will be determined
                            }
                            
                            # Calculate overall quality score
                            quality_data['overall_quality_score'] = (
                                quality_data['detection_confidence'] * 0.3 +
                                quality_data['face_size_score'] * 0.25 +
                                quality_data['face_angle_score'] * 0.25 +
                                quality_data['face_illumination_score'] * 0.2
                            )
                            
                            # Determine quality assessment
                            if quality_data['overall_quality_score'] >= 0.8:
                                quality_data['quality_assessment'] = 'excellent'
                            elif quality_data['overall_quality_score'] >= 0.6:
                                quality_data['quality_assessment'] = 'good'
                            elif quality_data['overall_quality_score'] >= 0.4:
                                quality_data['quality_assessment'] = 'fair'
                            else:
                                quality_data['quality_assessment'] = 'poor'
                            
                            quality_assessments.append(quality_data)
                            logger.info(f"  🧑 Face {i}: quality={quality_data['quality_assessment']} (score={quality_data['overall_quality_score']:.3f})")
                    
                    features.append({
                        'type': 'face_quality_assessment',
                        'domain': 'visual',
                        'confidence': 0.8,
                        'data': {
                            'quality_assessments': quality_assessments,
                            'total_faces_assessed': len(quality_assessments),
                            'excellent_faces': len([q for q in quality_assessments if q['quality_assessment'] == 'excellent']),
                            'good_faces': len([q for q in quality_assessments if q['quality_assessment'] == 'good']),
                            'fair_faces': len([q for q in quality_assessments if q['quality_assessment'] == 'fair']),
                            'poor_faces': len([q for q in quality_assessments if q['quality_assessment'] == 'poor']),
                            'assessment_method': 'FaceNet-MTCNN',
                            'status': 'completed'
                        },
                        'metadata': {'analyzer': 'facenet_quality'}
                    })
                    success_count += 1
                    logger.info(f"✅ Face quality assessment completed: {len(quality_assessments)} faces assessed")
                else:
                    logger.warning("⚠️ FaceNet not available for quality assessment")
                    features.append({
                        'type': 'face_quality_assessment',
                        'domain': 'visual',
                        'confidence': 0.0,
                        'data': {
                            'quality_assessments': [],
                            'total_faces_assessed': 0,
                            'assessment_method': 'FaceNet-MTCNN',
                            'status': 'unavailable',
                            'error': 'FaceNet not available'
                        },
                        'metadata': {'analyzer': 'facenet_quality'}
                    })
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ Face quality assessment error: {e}")
                features.append({
                    'type': 'face_quality_assessment',
                    'domain': 'visual',
                    'confidence': 0.0,
                    'data': {
                        'quality_assessments': [],
                        'total_faces_assessed': 0,
                        'assessment_method': 'FaceNet-MTCNN',
                        'status': 'error',
                        'error': str(e)
                    },
                    'metadata': {'analyzer': 'facenet_quality'}
                })
                success_count += 1
            
            logger.info(f"🎯 FaceNet analysis complete: {success_count}/{total_attempts} analyzers successful!")
            
            # Create result
            result = {
                'segments': [],
                'features': features,
                'embeddings': embeddings,
                'metadata': {
                    'analysis_version': '1.0-facenet',
                    'analyzer': 'facenet',
                    'device': self.device,
                    'models_used': ['MTCNN', 'FaceNet-InceptionResnetV1'] if FACENET_AVAILABLE else [],
                    'faces_processed': len(embeddings)
                }
            }
            
            logger.info(f"Completed FaceNetAnalyzer analysis for {file_path}: {len(result.get('segments', []))} segments, {len(result.get('features', []))} features, {len(result.get('embeddings', []))} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"FaceNet analysis failed: {str(e)}")
            return {
                'segments': [],
                'features': [],
                'embeddings': [],
                'metadata': {
                    'error': str(e),
                    'analysis_version': '1.0-facenet',
                    'analyzer': 'facenet'
                }
            }
    
    async def _initialize_models(self):
        """Initialize FaceNet models"""
        try:
            if FACENET_AVAILABLE:
                logger.info("🚀 Initializing FaceNet models...")
                
                # Initialize MTCNN for face detection
                self.mtcnn = MTCNN(
                    image_size=160,
                    margin=0,
                    min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7],  # P-Net, R-Net, O-Net thresholds
                    factor=0.709,
                    post_process=True,
                    device=self.device
                )
                
                # Initialize FaceNet model for face recognition
                self.facenet_model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
                
                self._models_initialized = True
                logger.info(f"✅ FaceNet models initialized successfully on {self.device}")
            else:
                logger.warning("⚠️ FaceNet not available - models not initialized")
                
        except Exception as e:
            logger.error(f"❌ FaceNet model initialization failed: {e}")
            self._models_initialized = False
    
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
    
    async def _find_best_match(self, embedding: torch.Tensor, threshold: float = 0.6) -> Dict[str, Any]:
        """Find best match for face embedding in database"""
        try:
            best_match = {
                'identity': 'unknown',
                'confidence': 0.0,
                'distance': float('inf')
            }
            
            if not self.face_embeddings:
                return best_match
            
            embedding_np = embedding.cpu().numpy()
            
            for identity, stored_embedding in self.face_embeddings.items():
                # Calculate cosine similarity
                similarity = np.dot(embedding_np, stored_embedding) / (
                    np.linalg.norm(embedding_np) * np.linalg.norm(stored_embedding)
                )
                
                distance = 1 - similarity
                
                if distance < best_match['distance']:
                    best_match = {
                        'identity': identity,
                        'confidence': similarity,
                        'distance': distance
                    }
            
            return best_match
            
        except Exception as e:
            logger.error(f"Face matching failed: {e}")
            return {'identity': 'unknown', 'confidence': 0.0, 'distance': float('inf')}
    
    def _assess_face_quality(self, embedding: torch.Tensor) -> str:
        """Assess face quality based on embedding characteristics"""
        try:
            # Simple quality assessment based on embedding norm and variance
            embedding_np = embedding.cpu().numpy()
            
            # Check embedding norm (should be close to 1 for normalized embeddings)
            norm = np.linalg.norm(embedding_np)
            norm_score = 1.0 - abs(norm - 1.0)
            
            # Check embedding variance (higher variance might indicate better quality)
            variance = np.var(embedding_np)
            variance_score = min(variance * 10, 1.0)  # Scale variance
            
            quality_score = (norm_score + variance_score) / 2
            
            if quality_score >= 0.8:
                return 'excellent'
            elif quality_score >= 0.6:
                return 'good'
            elif quality_score >= 0.4:
                return 'fair'
            else:
                return 'poor'
                
        except Exception as e:
            logger.error(f"Face quality assessment failed: {e}")
            return 'unknown'
    
    def _calculate_size_score(self, box: np.ndarray) -> float:
        """Calculate face size quality score"""
        try:
            width = box[2] - box[0]
            height = box[3] - box[1]
            area = width * height
            
            # Optimal face size is around 100x100 pixels
            optimal_size = 100 * 100
            size_ratio = min(area / optimal_size, optimal_size / area)
            
            return min(size_ratio, 1.0)
            
        except Exception as e:
            logger.error(f"Size score calculation failed: {e}")
            return 0.5
    
    def _calculate_angle_score(self, landmarks: np.ndarray) -> float:
        """Calculate face angle quality score based on landmarks"""
        try:
            if landmarks is None or len(landmarks) != 5:
                return 0.5
            
            # Calculate face angle based on eye positions
            left_eye = landmarks[0]
            right_eye = landmarks[1]
            
            # Calculate angle
            angle = np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])
            angle_degrees = abs(np.degrees(angle))
            
            # Score based on how close to horizontal (0 degrees)
            angle_score = 1.0 - min(angle_degrees / 45.0, 1.0)  # Penalty for angles > 45 degrees
            
            return max(angle_score, 0.0)
            
        except Exception as e:
            logger.error(f"Angle score calculation failed: {e}")
            return 0.5
    
    def _calculate_illumination_score(self, image: np.ndarray, box: np.ndarray) -> float:
        """Calculate face illumination quality score"""
        try:
            # Extract face region
            x1, y1, x2, y2 = map(int, box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            
            face_region = image[y1:y2, x1:x2]
            
            if face_region.size == 0:
                return 0.5
            
            # Convert to grayscale
            gray_face = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
            
            # Calculate illumination metrics
            mean_brightness = np.mean(gray_face)
            brightness_std = np.std(gray_face)
            
            # Optimal brightness is around 128 (middle of 0-255 range)
            brightness_score = 1.0 - abs(mean_brightness - 128) / 128
            
            # Good illumination has moderate contrast (not too flat, not too harsh)
            contrast_score = min(brightness_std / 50, 1.0)  # Optimal std around 50
            
            illumination_score = (brightness_score + contrast_score) / 2
            
            return max(illumination_score, 0.0)
            
        except Exception as e:
            logger.error(f"Illumination score calculation failed: {e}")
            return 0.5
    
    async def add_face_to_database(self, image_path: str, identity: str) -> bool:
        """Add a face to the recognition database"""
        try:
            if not FACENET_AVAILABLE or not self._models_initialized:
                logger.error("FaceNet not available for database operations")
                return False
            
            # Load and process image
            image = await self._load_image(image_path)
            if image is None:
                return False
            
            pil_image = Image.fromarray(image)
            
            # Extract face
            face_crop = self.mtcnn(pil_image)
            if face_crop is None:
                logger.error(f"No face detected in {image_path}")
                return False
            
            # Generate embedding
            face_crop = face_crop.to(self.device)
            with torch.no_grad():
                embedding = self.facenet_model(face_crop)
                embedding = embedding / torch.norm(embedding)
            
            # Store in database
            self.face_database[identity] = {
                'embedding': embedding.cpu().numpy(),
                'image_path': image_path,
                'added_at': str(asyncio.get_event_loop().time())
            }
            
            logger.info(f"✅ Added face for identity '{identity}' to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add face to database: {e}")
            return False
    
    def _load_face_database(self):
        """Load face database from file"""
        try:
            if os.path.exists(self.face_database_file):
                with open(self.face_database_file, 'r') as f:
                    data = json.load(f)
                    self.face_database = data.get('face_database', {})
                    # Convert embeddings back to numpy arrays
                    for face_id, face_info in self.face_database.items():
                        if 'embedding' in face_info:
                            self.face_embeddings[face_id] = np.array(face_info['embedding'])
                logger.info(f"✅ Loaded {len(self.face_database)} faces from database")
            else:
                logger.info("📝 No existing face database found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load face database: {e}")
            self.face_database = {}
            self.face_embeddings = {}
    
    def _save_face_database(self):
        """Save face database to file"""
        try:
            # Convert numpy arrays to lists for JSON serialization
            data_to_save = {}
            for face_id, face_info in self.face_database.items():
                data_to_save[face_id] = face_info.copy()
                if 'embedding' in face_info:
                    # Handle both numpy arrays and lists
                    embedding = face_info['embedding']
                    if hasattr(embedding, 'tolist'):
                        data_to_save[face_id]['embedding'] = embedding.tolist()
                    else:
                        data_to_save[face_id]['embedding'] = embedding
            
            with open(self.face_database_file, 'w') as f:
                json.dump({'face_database': data_to_save}, f, indent=2)
            logger.info(f"💾 Saved {len(self.face_database)} faces to database")
        except Exception as e:
            logger.error(f"Failed to save face database: {e}")
    
    def _create_face_avatar(self, face_crop: torch.Tensor, face_id: str) -> Optional[str]:
        """Create an avatar image from face crop and save it"""
        try:
            # Convert tensor to PIL Image
            if len(face_crop.shape) == 4:  # Batch dimension
                face_crop = face_crop.squeeze(0)
            
            # Convert tensor to numpy array
            face_array = face_crop.cpu().numpy()
            
            # Convert from CHW to HWC format
            if face_array.shape[0] == 3:  # RGB channels first
                face_array = np.transpose(face_array, (1, 2, 0))
            
            # Normalize from [-1, 1] to [0, 255] if needed
            if face_array.min() < 0:
                face_array = (face_array + 1) * 127.5
            face_array = np.clip(face_array, 0, 255).astype(np.uint8)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(face_array)
            
            # Resize to standard avatar size (128x128)
            pil_image = pil_image.resize((128, 128), Image.Resampling.LANCZOS)
            
            # Create avatar directory if it doesn't exist
            avatar_dir = "/tmp/dataflux_avatars"
            os.makedirs(avatar_dir, exist_ok=True)
            
            # Save avatar image
            avatar_filename = f"{face_id}_avatar.jpg"
            avatar_path = os.path.join(avatar_dir, avatar_filename)
            pil_image.save(avatar_path, "JPEG", quality=85)
            
            logger.info(f"📸 Avatar created: {avatar_filename}")
            return avatar_filename
            
        except Exception as e:
            logger.error(f"Failed to create face avatar: {e}")
            return None

    def _get_avatar_base64(self, avatar_filename: str) -> Optional[str]:
        """Get base64 encoded avatar image"""
        try:
            avatar_dir = "/tmp/dataflux_avatars"
            avatar_path = os.path.join(avatar_dir, avatar_filename)
            
            if not os.path.exists(avatar_path):
                logger.warning(f"Avatar file not found: {avatar_path}")
                return None
            
            with open(avatar_path, "rb") as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_data}"
                
        except Exception as e:
            logger.error(f"Failed to get avatar base64: {e}")
            return None
    
    def _generate_face_id(self, embedding: np.ndarray) -> str:
        """Generate a unique face ID based on embedding hash"""
        try:
            embedding_hash = hashlib.md5(embedding.tobytes()).hexdigest()[:8]
            timestamp = str(int(asyncio.get_event_loop().time() * 1000))[-6:]
            return f"face_{embedding_hash}_{timestamp}"
        except Exception as e:
            logger.error(f"Failed to generate face ID: {e}")
            return f"face_{uuid.uuid4().hex[:8]}"
    
    async def _find_best_match_enhanced(self, embedding: torch.Tensor, threshold: float = 0.6) -> Dict[str, Any]:
        """Enhanced face matching with unique IDs and database persistence"""
        try:
            logger.info(f"🔍 _find_best_match_enhanced called with threshold {threshold}")
            embedding_np = embedding.cpu().numpy()
            
            best_match = {
                'face_id': None,
                'identity': 'unknown',
                'confidence': 0.0,
                'distance': float('inf'),
                'is_new_face': True
            }
            
            if not self.face_embeddings:
                logger.info("📭 No faces in database, creating first face")
                # No faces in database yet, this is definitely a new face
                new_face_id = self._generate_face_id(embedding_np)
                best_match = {
                    'face_id': new_face_id,
                    'identity': f'Person_{new_face_id}',
                    'confidence': 1.0,  # Perfect match for first face
                    'distance': 0.0,
                    'is_new_face': True,
                    'first_seen': str(asyncio.get_event_loop().time()),
                    'last_seen': str(asyncio.get_event_loop().time()),
                    'appearance_count': 1
                }
                
                # Add to database
                self.face_database[new_face_id] = {
                    'identity': best_match['identity'],
                    'embedding': embedding_np,
                    'first_seen': best_match['first_seen'],
                    'last_seen': best_match['last_seen'],
                    'appearance_count': 1,
                    'created_at': str(asyncio.get_event_loop().time())
                }
                self.face_embeddings[new_face_id] = embedding_np
                
                # Save database
                self._save_face_database()
                logger.info(f"🆕 First face added to database: {new_face_id}")
                return best_match
            
            for face_id, stored_embedding in self.face_embeddings.items():
                # Calculate cosine similarity
                similarity = np.dot(embedding_np, stored_embedding) / (
                    np.linalg.norm(embedding_np) * np.linalg.norm(stored_embedding)
                )
                
                distance = 1 - similarity
                
                if distance < best_match['distance']:
                    face_info = self.face_database.get(face_id, {})
                    best_match = {
                        'face_id': face_id,
                        'identity': face_info.get('identity', f'Person_{face_id}'),
                        'confidence': similarity,
                        'distance': distance,
                        'is_new_face': False,
                        'first_seen': face_info.get('first_seen'),
                        'last_seen': face_info.get('last_seen'),
                        'appearance_count': face_info.get('appearance_count', 0)
                    }
            
            # If confidence is above threshold, it's a known face
            if best_match['confidence'] >= threshold:
                best_match['is_new_face'] = False
                # Update appearance count and last seen
                if best_match['face_id'] in self.face_database:
                    self.face_database[best_match['face_id']]['last_seen'] = str(asyncio.get_event_loop().time())
                    self.face_database[best_match['face_id']]['appearance_count'] += 1
                    # Save database after update
                    self._save_face_database()
                    logger.info(f"🔄 Updated known face: {best_match['face_id']}")
            else:
                # It's a new face, generate new ID
                new_face_id = self._generate_face_id(embedding_np)
                best_match['face_id'] = new_face_id
                best_match['identity'] = f'Person_{new_face_id}'
                best_match['is_new_face'] = True
                
                # Add to database
                self.face_database[new_face_id] = {
                    'identity': best_match['identity'],
                    'embedding': embedding_np,
                    'first_seen': str(asyncio.get_event_loop().time()),
                    'last_seen': str(asyncio.get_event_loop().time()),
                    'appearance_count': 1,
                    'created_at': str(asyncio.get_event_loop().time())
                }
                self.face_embeddings[new_face_id] = embedding_np
                
                # Save database
                self._save_face_database()
                logger.info(f"🆕 New face detected: {new_face_id}")
            
            return best_match
            
        except Exception as e:
            logger.error(f"Enhanced face matching failed: {e}")
            return {'face_id': None, 'identity': 'unknown', 'confidence': 0.0, 'distance': float('inf'), 'is_new_face': True}
    
    async def recognize_faces_in_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Recognize all faces in an image"""
        try:
            result = await self.analyze(image_path, {})
            
            recognized_faces = []
            for feature in result.get('features', []):
                if feature['type'] == 'face_recognition':
                    recognized_faces.extend(feature['data'].get('recognized_faces', []))
            
            return recognized_faces
            
        except Exception as e:
            logger.error(f"Face recognition failed: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the face database"""
        return {
            'total_identities': len(self.face_database),
            'total_embeddings': len(self.face_embeddings),
            'models_initialized': self._models_initialized,
            'device': self.device,
            'facenet_available': FACENET_AVAILABLE
        }
