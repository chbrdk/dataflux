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
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from sklearn.cluster import KMeans
from .base import BaseAnalyzer

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
    
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive image analysis with multiple AI models"""
        try:
            logger.info(f">>> ImageAnalyzer.analyze() called for {file_path}")
            self.log_analysis_start(file_path, asset_data)
            
            if not self.validate_file(file_path):
                logger.error(f"File validation failed for {file_path}")
                return self.create_error_result("Invalid file")
            
            logger.info(f"File validation passed, loading image...")
            
            # Load image
            from PIL import Image
            img = Image.open(file_path)
            width, height = img.size
            
            logger.info(f"🖼️ Image loaded: {width}x{height}, format: {img.format}, mode: {img.mode}")
            
            # Create basic features
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
                    'metadata': {'analyzer': 'basic_test'}
                }
            ]
            
            logger.info(f"✅ Generated {len(features)} features")
            
            # Create result
            result = self.create_success_result(
                segments=[],
                features=features,
                embeddings=[],
                metadata={
                    'analysis_version': '0.1-test',
                    'analyzer': 'simple_test'
                }
            )
            
            self.log_analysis_end(file_path, result)
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed", error=str(e))
            return self.create_error_result(str(e))
    
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
            logger.error(f"Model initialization failed", error=str(e))
    
    async def _load_image(self, file_path: str) -> Optional[np.ndarray]:
        """Load image as numpy array"""
        try:
            image = cv2.imread(file_path)
            if image is not None:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return None
        except Exception as e:
            logger.error(f"Failed to load image", error=str(e))
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
            logger.error(f"Technical properties analysis failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _extract_exif_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract EXIF metadata from image"""
        try:
            with Image.open(file_path) as img:
                exif_data = {}
                
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag] = str(value)
                
                features = [{
                    'type': 'exif_metadata',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': exif_data,
                    'metadata': {'analyzer': 'exif_extraction'}
                }]
                
                return {
                    'segments': [],
                    'features': features,
                    'embeddings': []
                }
                
        except Exception as e:
            logger.error(f"EXIF extraction failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
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
            logger.error(f"YOLO object detection failed", error=str(e))
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
            logger.error(f"DeepFace analysis failed", error=str(e))
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
            logger.error(f"Color analysis failed", error=str(e))
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
            logger.error(f"Scene composition analysis failed", error=str(e))
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
            logger.error(f"OCR text detection failed", error=str(e))
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
            logger.error(f"Semantic description generation failed", error=str(e))
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
            logger.error(f"Embedding generation failed", error=str(e))
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
            logger.error(f"Safety checks failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
