"""
Scene Analyzer for Video Analysis
Analyzes individual scene videos using various AI models
"""

import cv2
import numpy as np
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from .scene_extractor import ExtractedScene
from .base import BaseAnalyzer, Segment, AnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class SceneAnalysisResult:
    """Result of scene analysis"""
    scene_id: str
    features: List[Dict[str, Any]]
    embeddings: Dict[str, np.ndarray]
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]

class SceneAnalyzer(BaseAnalyzer):
    """Analyzes individual scene videos"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {
            'frame_sampling_rate': 0.5,  # Sample every 0.5 seconds
            'max_frames_per_scene': 10,
            'enable_object_detection': True,
            'enable_scene_classification': True,
            'enable_color_analysis': True,
            'enable_motion_analysis': True,
            'enable_quality_assessment': True
        }
        
        # Initialize analyzers
        self._init_analyzers()
        
        logger.info(f"🎬 Scene Analyzer initialized with {len(self.analyzers)} analyzers")
    
    def _init_analyzers(self):
        """Initialize available analyzers"""
        self.analyzers = {}
        
        # Object Detection (YOLO)
        if self.config.get('enable_object_detection', True):
            try:
                from .object_detector import ObjectDetector
                self.analyzers['object_detection'] = ObjectDetector()
                logger.info("✅ Object Detection analyzer loaded")
            except ImportError:
                logger.warning("⚠️ Object Detection analyzer not available")
        
        # Scene Classification (CLIP)
        if self.config.get('enable_scene_classification', True):
            try:
                from .scene_classifier import SceneClassifier
                self.analyzers['scene_classification'] = SceneClassifier()
                logger.info("✅ Scene Classification analyzer loaded")
            except ImportError:
                logger.warning("⚠️ Scene Classification analyzer not available")
        
        # Color Analysis
        if self.config.get('enable_color_analysis', True):
            try:
                from .color_analyzer import ColorAnalyzer
                self.analyzers['color_analysis'] = ColorAnalyzer()
                logger.info("✅ Color Analysis analyzer loaded")
            except ImportError:
                logger.warning("⚠️ Color Analysis analyzer not available")
        
        # Motion Analysis
        if self.config.get('enable_motion_analysis', True):
            try:
                from .motion_analyzer import MotionAnalyzer
                self.analyzers['motion_analysis'] = MotionAnalyzer()
                logger.info("✅ Motion Analysis analyzer loaded")
            except ImportError:
                logger.warning("⚠️ Motion Analysis analyzer not available")
        
        # Quality Assessment
        if self.config.get('enable_quality_assessment', True):
            try:
                from .quality_analyzer import QualityAnalyzer
                self.analyzers['quality_assessment'] = QualityAnalyzer()
                logger.info("✅ Quality Assessment analyzer loaded")
            except ImportError:
                logger.warning("⚠️ Quality Assessment analyzer not available")
    
    async def analyze_scene(self, extracted_scene: ExtractedScene) -> SceneAnalysisResult:
        """
        Analyze a single extracted scene
        
        Args:
            extracted_scene: ExtractedScene object
            
        Returns:
            SceneAnalysisResult object
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"🔍 Analyzing scene: {extracted_scene.scene_id}")
            
            # Extract representative frames
            frames = self._extract_representative_frames(extracted_scene)
            logger.info(f"📸 Extracted {len(frames)} representative frames")
            
            # Analyze frames
            all_features = []
            all_embeddings = {}
            
            for frame_data in frames:
                frame_features, frame_embeddings = await self._analyze_frame(frame_data)
                all_features.extend(frame_features)
                all_embeddings.update(frame_embeddings)
            
            # Analyze scene-level properties
            scene_features = await self._analyze_scene_properties(extracted_scene)
            all_features.extend(scene_features)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(all_features)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            result = SceneAnalysisResult(
                scene_id=extracted_scene.scene_id,
                features=all_features,
                embeddings=all_embeddings,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'frame_count': len(frames),
                    'feature_count': len(all_features),
                    'embedding_count': len(all_embeddings),
                    'scene_duration': extracted_scene.duration,
                    'scene_resolution': extracted_scene.resolution,
                    'scene_fps': extracted_scene.fps
                }
            )
            
            logger.info(f"✅ Scene analysis completed: {extracted_scene.scene_id} "
                       f"({len(all_features)} features, {processing_time:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Scene analysis failed for {extracted_scene.scene_id}: {e}")
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return SceneAnalysisResult(
                scene_id=extracted_scene.scene_id,
                features=[],
                embeddings={},
                confidence=0.0,
                processing_time=processing_time,
                metadata={'error': str(e)}
            )
    
    def _extract_representative_frames(self, extracted_scene: ExtractedScene) -> List[Dict[str, Any]]:
        """Extract representative frames from scene"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(extracted_scene.video_path)
            if not cap.isOpened():
                return frames
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate frame sampling
            sample_interval = max(1, int(fps * self.config['frame_sampling_rate']))
            max_frames = min(self.config['max_frames_per_scene'], total_frames)
            
            frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            
            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    timestamp = frame_idx / fps
                    
                    frames.append({
                        'frame': frame,
                        'frame_index': frame_idx,
                        'timestamp': timestamp,
                        'scene_id': extracted_scene.scene_id,
                        'metadata': {
                            'scene_duration': extracted_scene.duration,
                            'scene_resolution': extracted_scene.resolution,
                            'scene_fps': extracted_scene.fps
                        }
                    })
            
            cap.release()
            
        except Exception as e:
            logger.error(f"❌ Failed to extract frames from scene {extracted_scene.scene_id}: {e}")
        
        return frames
    
    async def _analyze_frame(self, frame_data: Dict[str, Any]) -> tuple:
        """Analyze a single frame"""
        features = []
        embeddings = {}
        
        frame = frame_data['frame']
        timestamp = frame_data['timestamp']
        scene_id = frame_data['scene_id']
        
        # Run all available analyzers
        for analyzer_name, analyzer in self.analyzers.items():
            try:
                if hasattr(analyzer, 'analyze_frame'):
                    result = await analyzer.analyze_frame(frame)
                    
                    if isinstance(result, dict):
                        # Add metadata
                        result['metadata'] = {
                            **result.get('metadata', {}),
                            'analyzer': analyzer_name,
                            'timestamp': timestamp,
                            'scene_id': scene_id
                        }
                        
                        features.append(result)
                        
                        # Extract embeddings if available
                        if 'embeddings' in result:
                            embeddings.update(result['embeddings'])
                
            except Exception as e:
                logger.error(f"❌ Analyzer {analyzer_name} failed: {e}")
        
        return features, embeddings
    
    async def _analyze_scene_properties(self, extracted_scene: ExtractedScene) -> List[Dict[str, Any]]:
        """Analyze scene-level properties"""
        features = []
        
        try:
            # Scene duration analysis
            duration_feature = {
                'type': 'scene_duration',
                'domain': 'temporal',
                'confidence': 1.0,
                'data': {
                    'duration': extracted_scene.duration,
                    'duration_category': self._categorize_duration(extracted_scene.duration),
                    'scene_id': extracted_scene.scene_id
                },
                'metadata': {
                    'analyzer': 'scene_analyzer',
                    'scene_id': extracted_scene.scene_id
                }
            }
            features.append(duration_feature)
            
            # Scene resolution analysis
            resolution_feature = {
                'type': 'scene_resolution',
                'domain': 'technical',
                'confidence': 1.0,
                'data': {
                    'width': extracted_scene.resolution[0],
                    'height': extracted_scene.resolution[1],
                    'aspect_ratio': extracted_scene.resolution[0] / extracted_scene.resolution[1],
                    'pixel_count': extracted_scene.resolution[0] * extracted_scene.resolution[1],
                    'scene_id': extracted_scene.scene_id
                },
                'metadata': {
                    'analyzer': 'scene_analyzer',
                    'scene_id': extracted_scene.scene_id
                }
            }
            features.append(resolution_feature)
            
            # Scene file size analysis
            size_feature = {
                'type': 'scene_file_size',
                'domain': 'technical',
                'confidence': 1.0,
                'data': {
                    'file_size_bytes': extracted_scene.file_size,
                    'file_size_mb': extracted_scene.file_size / (1024 * 1024),
                    'compression_ratio': extracted_scene.metadata.get('compression_ratio', 0),
                    'scene_id': extracted_scene.scene_id
                },
                'metadata': {
                    'analyzer': 'scene_analyzer',
                    'scene_id': extracted_scene.scene_id
                }
            }
            features.append(size_feature)
            
        except Exception as e:
            logger.error(f"❌ Scene properties analysis failed: {e}")
        
        return features
    
    def _categorize_duration(self, duration: float) -> str:
        """Categorize scene duration"""
        if duration < 1.0:
            return 'very_short'
        elif duration < 3.0:
            return 'short'
        elif duration < 10.0:
            return 'medium'
        elif duration < 30.0:
            return 'long'
        else:
            return 'very_long'
    
    def _calculate_confidence(self, features: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence score"""
        if not features:
            return 0.0
        
        confidences = [f.get('confidence', 0.0) for f in features]
        return sum(confidences) / len(confidences)
    
    # BaseAnalyzer interface methods
    def extract_segments(self, file_path: str) -> List[Segment]:
        """Extract segments from file (not used for scene analysis)"""
        return []
    
    async def analyze_segment(self, segment: Segment) -> AnalysisResult:
        """Analyze a segment (not used for scene analysis)"""
        return AnalysisResult(
            segment_id=segment.segment_id,
            analyzer_type='scene_analyzer',
            confidence=0.0,
            features=[],
            embeddings={},
            metadata={}
        )
    
    def generate_embeddings(self, segment: Segment) -> Dict[str, np.ndarray]:
        """Generate embeddings for segment (not used for scene analysis)"""
        return {}
    
    def get_memory_requirements(self) -> Dict[str, int]:
        """Get memory requirements"""
        return {
            'scene_analyzer': 100 * 1024 * 1024,  # 100MB
            'object_detection': 200 * 1024 * 1024,  # 200MB
            'scene_classification': 150 * 1024 * 1024,  # 150MB
            'color_analysis': 50 * 1024 * 1024,  # 50MB
            'motion_analysis': 100 * 1024 * 1024,  # 100MB
            'quality_assessment': 75 * 1024 * 1024  # 75MB
        }
    
    def get_supported_formats(self) -> List[str]:
        """Get supported video formats"""
        return ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']

# Factory function
def create_scene_analyzer(config: Dict[str, Any] = None) -> SceneAnalyzer:
    """Create a scene analyzer instance"""
    return SceneAnalyzer(config)
