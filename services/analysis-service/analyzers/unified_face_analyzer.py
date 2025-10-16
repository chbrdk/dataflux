"""
Unified Face Analyzer for DataFlux Analysis Service
Optimized workflow: FaceNet Detection → Database Check → DeepFace Demographics
Creates a single 'faces' feature combining all face data
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

# DeepFace imports
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

try:
    from .base import BaseAnalyzer
except ImportError:
    class BaseAnalyzer:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class UnifiedFaceAnalyzer(BaseAnalyzer):
    """
    Unified Face Analyzer with optimized workflow:
    1. FaceNet/MTCNN detects all faces
    2. Check database for known faces
    3. For each face, run DeepFace demographics
    4. Create single 'faces' feature with all data
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/bmp', 'image/tiff', 'image/webp'
        ]
        
        # Initialize device
        if torch and FACENET_AVAILABLE:
            if torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
                logger.info("🖥️ UnifiedFaceAnalyzer using CPU (MPS has compatibility issues with MTCNN)")
        else:
            self.device = "cpu"
        
        # Face database
        self.face_database = {}
        self.face_embeddings = {}
        self.face_database_file = "/tmp/dataflux_face_database.json"
        
        # Load existing face database
        self._load_face_database()
        
        # Models (lazy initialization)
        self.mtcnn = None
        self.facenet_model = None
        self._models_initialized = False
        
        logger.info(f"UnifiedFaceAnalyzer initialized on device: {self.device}")
    
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified face analysis workflow:
        1. Detect faces with FaceNet/MTCNN
        2. Check if faces are known or new
        3. Run DeepFace demographics for each detected face
        4. Return single 'faces' feature with complete data
        """
        try:
            logger.info(f"🧑 UnifiedFaceAnalyzer.analyze() called for {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return self._create_error_result("File not found")
            
            # Initialize models if needed
            if not self._models_initialized:
                await self._initialize_models()
            
            # Load image
            image = await self._load_image(file_path)
            if image is None:
                logger.error(f"Failed to load image: {file_path}")
                return self._create_error_result("Failed to load image")
            
            logger.info(f"🖼️ Image loaded: {image.shape}")
            
            # Resize for optimal processing
            image = await self._resize_image_for_processing(image)
            logger.info(f"🖼️ Final image size: {image.shape}")
            
            # STEP 1: Detect faces with FaceNet/MTCNN
            detected_faces = await self._detect_faces_with_facenet(image, file_path)
            
            if not detected_faces:
                logger.info("📭 No faces detected")
                return self._create_no_faces_result()
            
            logger.info(f"✅ Detected {len(detected_faces)} face(s)")
            
            # STEP 2: For each face, get recognition data and demographics
            unified_faces = []
            for i, face_data in enumerate(detected_faces):
                logger.info(f"🔍 Processing face {i+1}/{len(detected_faces)}...")
                
                # Get FaceNet recognition data
                recognition_data = face_data.get('recognition', {})
                
                # Run DeepFace demographics for this specific face
                demographics = await self._get_face_demographics(file_path, face_data.get('bbox'))
                
                # Combine all data into unified face object
                unified_face = {
                    'face_id': recognition_data.get('face_id'),
                    'face_index': i,
                    'identity': recognition_data.get('identity', 'unknown'),
                    'is_known': recognition_data.get('is_known_face', False),
                    'is_new': recognition_data.get('is_new_face', True),
                    'confidence': recognition_data.get('confidence', 0.0),
                    'appearance_count': recognition_data.get('appearance_count', 1),
                    'first_seen': recognition_data.get('first_seen'),
                    'last_seen': recognition_data.get('last_seen'),
                    'avatar_base64': recognition_data.get('avatar_base64'),
                    'avatar_filename': recognition_data.get('avatar_filename'),
                    'bbox': face_data.get('bbox'),
                    'detection_confidence': face_data.get('detection_confidence', 0.0),
                    'landmarks': face_data.get('landmarks', []),
                    'face_size': face_data.get('face_size', {}),
                    'face_quality': face_data.get('face_quality', {}),
                    'demographics': demographics,
                    'embedding_dimensions': recognition_data.get('embedding_dimensions', 512),
                    'embedding_key': recognition_data.get('embedding_key')
                }
                
                unified_faces.append(unified_face)
                
                logger.info(f"  ✅ Face {i+1}: {unified_face['identity']} ({'Known' if unified_face['is_known'] else 'New'})")
                if demographics:
                    logger.info(f"     📊 Demographics: Age {demographics.get('age')}, {demographics.get('gender')}, {demographics.get('emotion')}")
            
            # Create single unified 'faces' feature
            features = [{
                'type': 'faces',
                'domain': 'visual',
                'confidence': 0.9,
                'data': {
                    'faces': unified_faces,
                    'total_faces': len(unified_faces),
                    'known_faces': len([f for f in unified_faces if f['is_known']]),
                    'new_faces': len([f for f in unified_faces if f['is_new']]),
                    'detection_model': 'FaceNet-MTCNN',
                    'recognition_model': 'FaceNet-InceptionResnetV1',
                    'demographics_model': 'DeepFace',
                    'status': 'completed'
                },
                'metadata': {
                    'analyzer': 'unified_face_analyzer',
                    'device': self.device,
                    'workflow': 'facenet_detection → database_check → deepface_demographics'
                }
            }]
            
            # Create embeddings for database
            embeddings = []
            for face in unified_faces:
                if face.get('embedding_key'):
                    embeddings.append({
                        'type': 'visual',
                        'model': 'FaceNet-InceptionResnetV1',
                        'dimensions': face.get('embedding_dimensions', 512),
                        'face_id': face.get('face_id'),
                        'embedding_key': face.get('embedding_key'),
                        'metadata': {
                            'analyzer': 'unified_face_analyzer',
                            'device': self.device
                        }
                    })
            
            result = {
                'segments': [],
                'features': features,
                'embeddings': embeddings,
                'metadata': {
                    'analysis_version': '2.0-unified',
                    'analyzer': 'unified_face_analyzer',
                    'device': self.device,
                    'faces_processed': len(unified_faces)
                }
            }
            
            logger.info(f"🎯 UnifiedFaceAnalyzer complete: {len(unified_faces)} faces, 1 feature, {len(embeddings)} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"Unified face analysis failed: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._create_error_result(str(e))
    
    async def _detect_faces_with_facenet(self, image: np.ndarray, file_path: str) -> List[Dict[str, Any]]:
        """
        Step 1: Detect faces using FaceNet/MTCNN and get recognition data
        Returns list of detected faces with recognition info
        """
        try:
            if not FACENET_AVAILABLE or not self.mtcnn or not self.facenet_model:
                logger.warning("⚠️ FaceNet not available")
                return []
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image)
            
            # Detect faces and get bounding boxes
            boxes, probs, landmarks = self.mtcnn.detect(pil_image, landmarks=True)
            
            if boxes is None or len(boxes) == 0:
                logger.info("📭 No faces detected by MTCNN")
                return []
            
            logger.info(f"📊 MTCNN detected {len(boxes)} face(s)")
            
            # Extract face crops for recognition - USE keep_all=True to get ALL faces!
            face_crops = []
            for box in boxes:
                # Extract each face region manually
                x1, y1, x2, y2 = box
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Ensure coordinates are within image bounds
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(pil_image.width, x2)
                y2 = min(pil_image.height, y2)
                
                # Crop face from image
                face_crop = pil_image.crop((x1, y1, x2, y2))
                
                # Resize to 160x160 (MTCNN standard)
                face_crop = face_crop.resize((160, 160), Image.Resampling.BILINEAR)
                
                # Convert to tensor
                face_tensor = torch.from_numpy(np.array(face_crop)).float()
                face_tensor = face_tensor.permute(2, 0, 1)  # HWC to CHW
                face_tensor = (face_tensor - 127.5) / 128.0  # Normalize to [-1, 1]
                
                face_crops.append(face_tensor)
            
            if len(face_crops) == 0:
                logger.warning("⚠️ Could not extract face crops")
                return []
            
            # Stack all face crops into batch
            face_crops = torch.stack(face_crops)
            
            # Generate embeddings
            face_crops = face_crops.to(self.device)
            with torch.no_grad():
                face_embeddings = self.facenet_model(face_crops)
            
            # Process each detected face
            detected_faces = []
            logger.info(f"🔄 Processing {len(boxes)} detected faces...")
            for i, (box, prob, landmark, embedding) in enumerate(zip(boxes, probs, landmarks, face_embeddings)):
                # Normalize embedding
                embedding_norm = embedding / torch.norm(embedding)
                
                # Check database for match
                recognition_result = await self._find_best_match_enhanced(embedding_norm)
                
                logger.info(f"  👤 Face {i+1}/{len(boxes)}: {recognition_result['identity']} ({'New' if recognition_result['is_new_face'] else 'Known'})")
                
                # Create avatar for new faces
                if recognition_result['is_new_face']:
                    avatar_filename = self._create_face_avatar(face_crops[i], recognition_result['face_id'])
                    if avatar_filename:
                        if recognition_result['face_id'] in self.face_database:
                            self.face_database[recognition_result['face_id']]['avatar_filename'] = avatar_filename
                            self._save_face_database()
                        recognition_result['avatar_filename'] = avatar_filename
                        recognition_result['avatar_base64'] = self._get_avatar_base64(avatar_filename)
                else:
                    # Get existing avatar for known faces
                    if recognition_result['face_id'] in self.face_database:
                        avatar_filename = self.face_database[recognition_result['face_id']].get('avatar_filename')
                        if avatar_filename:
                            recognition_result['avatar_filename'] = avatar_filename
                            recognition_result['avatar_base64'] = self._get_avatar_base64(avatar_filename)
                
                # Calculate quality scores
                quality_data = {
                    'detection_confidence': float(prob),
                    'size_score': self._calculate_size_score(box),
                    'angle_score': self._calculate_angle_score(landmark) if landmark is not None else 0.5,
                    'illumination_score': self._calculate_illumination_score(image, box),
                    'overall_score': 0.0
                }
                quality_data['overall_score'] = (
                    quality_data['detection_confidence'] * 0.3 +
                    quality_data['size_score'] * 0.25 +
                    quality_data['angle_score'] * 0.25 +
                    quality_data['illumination_score'] * 0.2
                )
                
                # Determine quality level
                if quality_data['overall_score'] >= 0.8:
                    quality_level = 'excellent'
                elif quality_data['overall_score'] >= 0.6:
                    quality_level = 'good'
                elif quality_data['overall_score'] >= 0.4:
                    quality_level = 'fair'
                else:
                    quality_level = 'poor'
                
                quality_data['level'] = quality_level
                
                # Create face data object
                face_data = {
                    'bbox': box.tolist(),
                    'detection_confidence': float(prob),
                    'landmarks': landmark.tolist() if landmark is not None else [],
                    'face_size': {
                        'width': float(box[2] - box[0]),
                        'height': float(box[3] - box[1]),
                        'area': float((box[2] - box[0]) * (box[3] - box[1]))
                    },
                    'face_quality': quality_data,
                    'recognition': recognition_result
                }
                
                detected_faces.append(face_data)
                
                logger.info(f"  🧑 Face {i}: {recognition_result['identity']} ({'Known' if not recognition_result['is_new_face'] else 'New'}), confidence={prob:.3f}")
            
            return detected_faces
            
        except Exception as e:
            logger.error(f"FaceNet face detection failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _get_face_demographics(self, file_path: str, bbox: List[float]) -> Optional[Dict[str, Any]]:
        """
        Step 3: Get demographics for a specific face using DeepFace
        Crops the face region and analyzes it
        """
        try:
            if not DEEPFACE_AVAILABLE:
                logger.warning("⚠️ DeepFace not available")
                return None
            
            # Read image
            img = cv2.imread(file_path)
            if img is None:
                return None
            
            # Crop face region (with some margin)
            x1, y1, x2, y2 = map(int, bbox)
            
            # Add margin (10%)
            margin_x = int((x2 - x1) * 0.1)
            margin_y = int((y2 - y1) * 0.1)
            
            x1 = max(0, x1 - margin_x)
            y1 = max(0, y1 - margin_y)
            x2 = min(img.shape[1], x2 + margin_x)
            y2 = min(img.shape[0], y2 + margin_y)
            
            face_crop = img[y1:y2, x1:x2]
            
            if face_crop.size == 0:
                logger.warning(f"⚠️ Empty face crop for bbox {bbox}")
                return None
            
            # Save temporary crop for DeepFace
            temp_crop_path = f"/tmp/face_crop_{uuid.uuid4().hex}.jpg"
            cv2.imwrite(temp_crop_path, face_crop)
            
            try:
                # Analyze with DeepFace
                analysis = DeepFace.analyze(
                    img_path=temp_crop_path,
                    actions=['age', 'gender', 'race', 'emotion'],
                    enforce_detection=False,
                    silent=True
                )
                
                # Handle single result or list
                if isinstance(analysis, list):
                    analysis = analysis[0] if analysis else {}
                
                demographics = {
                    'age': analysis.get('age'),
                    'gender': analysis.get('dominant_gender'),
                    'race': analysis.get('dominant_race'),
                    'emotion': analysis.get('dominant_emotion'),
                    'gender_confidence': analysis.get('gender', {}),
                    'race_confidence': analysis.get('race', {}),
                    'emotion_confidence': analysis.get('emotion', {})
                }
                
                return demographics
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_crop_path):
                    os.remove(temp_crop_path)
            
        except Exception as e:
            logger.error(f"DeepFace demographics failed: {e}")
            return None
    
    async def _resize_image_for_processing(self, image: np.ndarray) -> np.ndarray:
        """Resize image for optimal FaceNet processing"""
        max_dimension = 1920
        height, width = image.shape[:2]
        
        if height > max_dimension or width > max_dimension:
            if height > width:
                new_height = max_dimension
                new_width = int((width * max_dimension) / height)
            else:
                new_width = max_dimension
                new_height = int((height * max_dimension) / width)
            
            # Ensure dimensions divisible by 8 for MPS
            new_width = (new_width // 8) * 8
            new_height = (new_height // 8) * 8
            
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"✅ Image resized to {new_width}x{new_height}")
        
        return image
    
    async def _initialize_models(self):
        """Initialize FaceNet models"""
        try:
            if FACENET_AVAILABLE:
                logger.info("🚀 Initializing FaceNet models...")
                
                self.mtcnn = MTCNN(
                    image_size=160,
                    margin=0,
                    min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7],
                    factor=0.709,
                    post_process=True,
                    device=self.device
                )
                
                self.facenet_model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
                
                self._models_initialized = True
                logger.info(f"✅ FaceNet models initialized on {self.device}")
            else:
                logger.warning("⚠️ FaceNet not available")
                
        except Exception as e:
            logger.error(f"❌ FaceNet initialization failed: {e}")
            self._models_initialized = False
    
    async def _load_image(self, file_path: str) -> Optional[np.ndarray]:
        """Load image as RGB numpy array"""
        try:
            image = cv2.imread(file_path)
            if image is not None:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return None
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None
    
    async def _find_best_match_enhanced(self, embedding: torch.Tensor, threshold: float = 0.6) -> Dict[str, Any]:
        """Enhanced face matching with database persistence"""
        try:
            embedding_np = embedding.cpu().numpy()
            
            best_match = {
                'face_id': None,
                'identity': 'unknown',
                'confidence': 0.0,
                'distance': float('inf'),
                'is_new_face': True,
                'is_known_face': False
            }
            
            # Check if database is empty
            if not self.face_embeddings:
                new_face_id = self._generate_face_id(embedding_np)
                best_match = {
                    'face_id': new_face_id,
                    'identity': f'Person_{new_face_id}',
                    'confidence': 1.0,
                    'distance': 0.0,
                    'is_new_face': True,
                    'is_known_face': False,
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
                    'appearance_count': 1
                }
                self.face_embeddings[new_face_id] = embedding_np
                self._save_face_database()
                
                logger.info(f"🆕 First face in database: {new_face_id}")
                return best_match
            
            # Find best match in database
            for face_id, stored_embedding in self.face_embeddings.items():
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
                        'is_known_face': True,
                        'first_seen': face_info.get('first_seen'),
                        'last_seen': face_info.get('last_seen'),
                        'appearance_count': face_info.get('appearance_count', 0)
                    }
            
            # Determine if match is above threshold
            if best_match['confidence'] >= threshold:
                # Known face - update stats
                best_match['is_new_face'] = False
                best_match['is_known_face'] = True
                
                if best_match['face_id'] in self.face_database:
                    self.face_database[best_match['face_id']]['last_seen'] = str(asyncio.get_event_loop().time())
                    self.face_database[best_match['face_id']]['appearance_count'] += 1
                    best_match['appearance_count'] = self.face_database[best_match['face_id']]['appearance_count']
                    self._save_face_database()
                    logger.info(f"🔄 Known face updated: {best_match['face_id']}")
            else:
                # New face - add to database
                new_face_id = self._generate_face_id(embedding_np)
                best_match = {
                    'face_id': new_face_id,
                    'identity': f'Person_{new_face_id}',
                    'confidence': 1.0,
                    'distance': 0.0,
                    'is_new_face': True,
                    'is_known_face': False,
                    'first_seen': str(asyncio.get_event_loop().time()),
                    'last_seen': str(asyncio.get_event_loop().time()),
                    'appearance_count': 1
                }
                
                self.face_database[new_face_id] = {
                    'identity': best_match['identity'],
                    'embedding': embedding_np,
                    'first_seen': best_match['first_seen'],
                    'last_seen': best_match['last_seen'],
                    'appearance_count': 1
                }
                self.face_embeddings[new_face_id] = embedding_np
                self._save_face_database()
                
                logger.info(f"🆕 New face added: {new_face_id}")
            
            # Add embedding info
            best_match['embedding_dimensions'] = len(embedding_np)
            best_match['embedding_key'] = f"face_{best_match['face_id']}"
            
            return best_match
            
        except Exception as e:
            logger.error(f"Face matching failed: {e}")
            return {
                'face_id': None,
                'identity': 'unknown',
                'confidence': 0.0,
                'distance': float('inf'),
                'is_new_face': True,
                'is_known_face': False
            }
    
    def _generate_face_id(self, embedding: np.ndarray) -> str:
        """Generate unique face ID"""
        try:
            embedding_hash = hashlib.md5(embedding.tobytes()).hexdigest()[:8]
            timestamp = str(int(asyncio.get_event_loop().time() * 1000))[-6:]
            return f"face_{embedding_hash}_{timestamp}"
        except Exception as e:
            logger.error(f"Face ID generation failed: {e}")
            return f"face_{uuid.uuid4().hex[:8]}"
    
    def _load_face_database(self):
        """Load face database from file"""
        try:
            if os.path.exists(self.face_database_file):
                with open(self.face_database_file, 'r') as f:
                    data = json.load(f)
                    self.face_database = data.get('face_database', {})
                    for face_id, face_info in self.face_database.items():
                        if 'embedding' in face_info:
                            self.face_embeddings[face_id] = np.array(face_info['embedding'])
                logger.info(f"✅ Loaded {len(self.face_database)} faces from database")
            else:
                logger.info("📝 No existing face database, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load face database: {e}")
            self.face_database = {}
            self.face_embeddings = {}
    
    def _save_face_database(self):
        """Save face database to file"""
        try:
            data_to_save = {}
            for face_id, face_info in self.face_database.items():
                data_to_save[face_id] = face_info.copy()
                if 'embedding' in face_info:
                    embedding = face_info['embedding']
                    if hasattr(embedding, 'tolist'):
                        data_to_save[face_id]['embedding'] = embedding.tolist()
            
            with open(self.face_database_file, 'w') as f:
                json.dump({'face_database': data_to_save}, f, indent=2)
            
            logger.info(f"💾 Saved {len(self.face_database)} faces to database")
        except Exception as e:
            logger.error(f"Failed to save face database: {e}")
    
    def _create_face_avatar(self, face_crop: torch.Tensor, face_id: str) -> Optional[str]:
        """Create avatar from face crop"""
        try:
            if len(face_crop.shape) == 4:
                face_crop = face_crop.squeeze(0)
            
            face_array = face_crop.cpu().numpy()
            
            if face_array.shape[0] == 3:
                face_array = np.transpose(face_array, (1, 2, 0))
            
            if face_array.min() < 0:
                face_array = (face_array + 1) * 127.5
            face_array = np.clip(face_array, 0, 255).astype(np.uint8)
            
            pil_image = Image.fromarray(face_array)
            pil_image = pil_image.resize((128, 128), Image.Resampling.LANCZOS)
            
            avatar_dir = "/tmp/dataflux_avatars"
            os.makedirs(avatar_dir, exist_ok=True)
            
            avatar_filename = f"{face_id}_avatar.jpg"
            avatar_path = os.path.join(avatar_dir, avatar_filename)
            pil_image.save(avatar_path, "JPEG", quality=85)
            
            logger.info(f"📸 Avatar created: {avatar_filename}")
            return avatar_filename
            
        except Exception as e:
            logger.error(f"Failed to create avatar: {e}")
            return None
    
    def _get_avatar_base64(self, avatar_filename: str) -> Optional[str]:
        """Get base64 encoded avatar"""
        try:
            avatar_path = os.path.join("/tmp/dataflux_avatars", avatar_filename)
            
            if not os.path.exists(avatar_path):
                return None
            
            with open(avatar_path, "rb") as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_data}"
                
        except Exception as e:
            logger.error(f"Failed to get avatar base64: {e}")
            return None
    
    def _calculate_size_score(self, box: np.ndarray) -> float:
        """Calculate face size quality score"""
        try:
            width = box[2] - box[0]
            height = box[3] - box[1]
            area = width * height
            optimal_size = 100 * 100
            size_ratio = min(area / optimal_size, optimal_size / area)
            return min(size_ratio, 1.0)
        except Exception as e:
            return 0.5
    
    def _calculate_angle_score(self, landmarks: np.ndarray) -> float:
        """Calculate face angle quality score"""
        try:
            if landmarks is None or len(landmarks) != 5:
                return 0.5
            
            left_eye = landmarks[0]
            right_eye = landmarks[1]
            angle = np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])
            angle_degrees = abs(np.degrees(angle))
            angle_score = 1.0 - min(angle_degrees / 45.0, 1.0)
            return max(angle_score, 0.0)
        except Exception as e:
            return 0.5
    
    def _calculate_illumination_score(self, image: np.ndarray, box: np.ndarray) -> float:
        """Calculate illumination quality score"""
        try:
            x1, y1, x2, y2 = map(int, box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            
            face_region = image[y1:y2, x1:x2]
            
            if face_region.size == 0:
                return 0.5
            
            gray_face = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
            mean_brightness = np.mean(gray_face)
            brightness_std = np.std(gray_face)
            
            brightness_score = 1.0 - abs(mean_brightness - 128) / 128
            contrast_score = min(brightness_std / 50, 1.0)
            illumination_score = (brightness_score + contrast_score) / 2
            
            return max(illumination_score, 0.0)
        except Exception as e:
            return 0.5
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'segments': [],
            'features': [],
            'embeddings': [],
            'metadata': {
                'error': error_message,
                'analysis_version': '2.0-unified',
                'analyzer': 'unified_face_analyzer'
            }
        }
    
    def _create_no_faces_result(self) -> Dict[str, Any]:
        """Create result for no faces detected"""
        return {
            'segments': [],
            'features': [{
                'type': 'faces',
                'domain': 'visual',
                'confidence': 0.9,
                'data': {
                    'faces': [],
                    'total_faces': 0,
                    'known_faces': 0,
                    'new_faces': 0,
                    'detection_model': 'FaceNet-MTCNN',
                    'status': 'no_faces_detected'
                },
                'metadata': {
                    'analyzer': 'unified_face_analyzer',
                    'device': self.device
                }
            }],
            'embeddings': [],
            'metadata': {
                'analysis_version': '2.0-unified',
                'analyzer': 'unified_face_analyzer',
                'faces_processed': 0
            }
        }

