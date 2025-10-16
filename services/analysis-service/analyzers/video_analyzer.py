"""
Enhanced Video Analyzer for DataFlux Analysis Service
Comprehensive video analysis with scene detection, frame extraction, and multi-modal analysis
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
from pathlib import Path
import time
import os
from datetime import datetime

from .base import BaseAnalyzer, Segment, AnalysisResult
from .video_config import get_video_config
from .scene_detector import AdvancedSceneDetector
from .frame_storage import FrameStorageManager, FrameData
from .audio_extractor import AudioExtractor
from .video_result_builder import HierarchicalResultBuilder
from .image_analyzer import ImageAnalyzer

# Import new enhanced features
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.models.model_manager import get_model_manager
from src.config import get_settings
from src.utils.memory import log_memory_stats

# Import new analyzers (optional - will be available after Docker rebuild)
try:
    from .object_tracker import ObjectTracker
    OBJECT_TRACKER_AVAILABLE = True
except ImportError:
    OBJECT_TRACKER_AVAILABLE = False

try:
    from .action_recognizer import ActionRecognizer
    ACTION_RECOGNIZER_AVAILABLE = True
except ImportError:
    ACTION_RECOGNIZER_AVAILABLE = False

try:
    from .pose_estimator import PoseEstimator
    POSE_ESTIMATOR_AVAILABLE = True
except ImportError:
    POSE_ESTIMATOR_AVAILABLE = False

try:
    from .depth_estimator import DepthEstimator
    DEPTH_ESTIMATOR_AVAILABLE = True
except ImportError:
    DEPTH_ESTIMATOR_AVAILABLE = False

try:
    from .quality_analyzer import QualityAnalyzer
    QUALITY_ANALYZER_AVAILABLE = True
except ImportError:
    QUALITY_ANALYZER_AVAILABLE = False

try:
    from .safety_analyzer import SafetyAnalyzer
    SAFETY_ANALYZER_AVAILABLE = True
except ImportError:
    SAFETY_ANALYZER_AVAILABLE = False

try:
    from .summarizer import VideoSummarizer
    VIDEO_SUMMARIZER_AVAILABLE = True
except ImportError:
    VIDEO_SUMMARIZER_AVAILABLE = False

logger = logging.getLogger(__name__)

class EnhancedVideoAnalyzer(BaseAnalyzer):
    """Enhanced video analyzer with comprehensive analysis pipeline"""
    
    def __init__(self):
        super().__init__()  # Initialize BaseAnalyzer
        self.supported_formats = [
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv',
            'video/webm', 'video/flv', 'video/wmv'
        ]
        
        # Initialize GPT-5 Vision Analyzer
        self._init_gpt5_vision_analyzer()
        
        # Initialize configuration and model manager
        self.settings = get_settings()
        self.model_manager = get_model_manager()
        self.config = get_video_config()
        
        # Log memory stats at startup
        log_memory_stats("EnhancedVideoAnalyzer startup")
        
        # Initialize core components
        self.scene_detector = AdvancedSceneDetector()
        self.audio_extractor = AudioExtractor()
        self.result_builder = HierarchicalResultBuilder()
        
        # Initialize image analyzer with video-specific configuration
        self.image_analyzer = ImageAnalyzer(claude_vision_mode=self.config.claude_vision_mode.value)
        
        # Initialize enhanced analyzers based on tier
        self._initialize_enhanced_analyzers()
        
        logger.info(f"Enhanced Video Analyzer initialized - Tier: {self.model_manager.get_current_tier()}")
    
    def _init_gpt5_vision_analyzer(self):
        """Initialize GPT-5 Vision Analyzer for comprehensive image analysis"""
        try:
            from .gpt5_vision_analyzer import create_gpt5_vision_analyzer, GPT5_VISION_AVAILABLE
            
            if GPT5_VISION_AVAILABLE:
                # Verwende GPT-5-nano für bessere Effizienz
                self.gpt5_vision_analyzer = create_gpt5_vision_analyzer(use_nano=True)
                if self.gpt5_vision_analyzer:
                    logger.info("🤖 GPT-5 Vision Analyzer (nano) successfully initialized")
                else:
                    logger.warning("⚠️ GPT-5 Vision Analyzer creation failed")
                    self.gpt5_vision_analyzer = None
            else:
                logger.warning("⚠️ GPT-5 Vision Analyzer not available")
                self.gpt5_vision_analyzer = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize GPT-5 Vision Analyzer: {e}")
            self.gpt5_vision_analyzer = None
    
    def _initialize_enhanced_analyzers(self):
        """Initialize enhanced analyzers based on current tier and availability"""
        tier = self.model_manager.get_current_tier()
        
        # Initialize available analyzers
        if OBJECT_TRACKER_AVAILABLE:
            self.object_tracker = ObjectTracker(self.model_manager)
            logger.info("Object Tracker initialized")
        
        if QUALITY_ANALYZER_AVAILABLE:
            self.quality_analyzer = QualityAnalyzer()
            logger.info("Quality Analyzer initialized")
        
        if SAFETY_ANALYZER_AVAILABLE:
            self.safety_analyzer = SafetyAnalyzer(self.model_manager)
            logger.info("Safety Analyzer initialized")
        
        # Initialize tier-specific analyzers
        if tier in ["standard", "pro"] and ACTION_RECOGNIZER_AVAILABLE:
            self.action_recognizer = ActionRecognizer(self.model_manager)
            logger.info("Action Recognition enabled (standard/pro tier)")
        
        if tier == "pro":
            if POSE_ESTIMATOR_AVAILABLE:
                self.pose_estimator = PoseEstimator(self.model_manager)
                logger.info("Pose Estimation enabled (pro tier)")
            
            if DEPTH_ESTIMATOR_AVAILABLE:
                self.depth_estimator = DepthEstimator(self.model_manager)
                logger.info("Depth Estimation enabled (pro tier)")
        
        # Initialize optional analyzers based on config
        if self.settings.video_analysis.enable_video_summarization and VIDEO_SUMMARIZER_AVAILABLE:
            self.video_summarizer = VideoSummarizer()
            logger.info("Video Summarization enabled")
        
        logger.info(f"Enhanced analyzers initialized for tier: {tier}")
        
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def extract_segments(self, file_path: str) -> List[Segment]:
        """
        Extrahiert Video-Segmente basierend auf Szenenwechseln
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                logger.error(f"❌ Could not open video file: {file_path}")
                return []
            
            # Hole Video-Informationen
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Verwende Scene Detector für Segmentierung
            segments = []
            if hasattr(self, 'scene_detector'):
                scene_detection_result = await self.scene_detector.detect_scenes(file_path)
                detected_scenes = scene_detection_result.scenes
                
                for i, scene_dict in enumerate(detected_scenes):
                    start_time = scene_dict.get('start_time', 0.0)
                    end_time = scene_dict.get('end_time', duration)
                    segment = Segment(
                        segment_id=f"scene_{i+1}",
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time,
                        metadata={
                            'scene_index': i,
                            'fps': fps,
                            'total_frames': total_frames,
                            'analyzer': 'enhanced_video_analyzer',
                            'scene_data': scene_dict
                        }
                    )
                    segments.append(segment)
            else:
                # Fallback: Einzelnes Segment für gesamtes Video
                segment = Segment(
                    segment_id="full_video",
                    start_time=0.0,
                    end_time=duration,
                    duration=duration,
                    metadata={
                        'fps': fps,
                        'total_frames': total_frames,
                        'analyzer': 'enhanced_video_analyzer'
                    }
                )
                segments.append(segment)
            
            cap.release()
            logger.info(f"✅ Extracted {len(segments)} segments from video")
            return segments
            
        except Exception as e:
            logger.error(f"❌ Failed to extract segments: {e}")
            return []
    
    async def analyze_segment(self, segment: Segment) -> AnalysisResult:
        """
        Analysiert ein einzelnes Video-Segment
        """
        try:
            # Extrahiere Frames aus dem Segment
            frames = self._extract_frames_from_segment(segment)
            
            features = []
            embeddings = {}
            
            # Analysiere jeden Frame
            for frame_data in frames:
                # GPT-5 Vision Analyse für Schlüsselbilder
                if hasattr(self, 'gpt5_vision_analyzer') and self.gpt5_vision_analyzer:
                    gpt5_result = await self.gpt5_vision_analyzer.analyze_image(frame_data['path'])
                    if gpt5_result.get('status') == 'completed':
                        features.append({
                            'type': 'gpt5_vision_analysis',
                            'frame_time': frame_data['timestamp'],
                            'confidence': 0.98,  # GPT-5 ist noch zuverlässiger
                            'data': gpt5_result,
                            'metadata': {
                                'analyzer': 'gpt5_vision',
                                'model': gpt5_result.get('model', 'gpt-5-nano'),
                                'tokens_used': gpt5_result.get('tokens_used', 0),
                                'is_nano': gpt5_result.get('is_nano', True)
                            }
                        })
                
                # Traditionelle Computer Vision Analyse
                cv_features = self._analyze_frame_cv(frame_data)
                features.extend(cv_features)
            
            # Generiere Embeddings für das Segment
            embeddings = self.generate_embeddings(segment)
            
            return AnalysisResult(
                segment_id=segment.segment_id,
                analyzer_type="enhanced_video_analyzer",
                features=features,
                embeddings=embeddings,
                confidence=0.8,
                metadata={
                    'segment_duration': segment.duration,
                    'frames_analyzed': len(frames),
                    'gpt5_analysis': hasattr(self, 'gpt5_vision_analyzer') and self.gpt5_vision_analyzer is not None
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze segment {segment.segment_id}: {e}")
            return AnalysisResult(
                segment_id=segment.segment_id,
                analyzer_type="enhanced_video_analyzer",
                features=[],
                embeddings={},
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    def generate_embeddings(self, segment: Segment) -> Dict[str, np.ndarray]:
        """
        Generiert Embeddings für ein Video-Segment
        """
        try:
            embeddings = {}
            
            # Extrahiere Frames für Embedding-Generierung
            frames = self._extract_frames_from_segment(segment)
            
            if frames:
                # Verwende den ersten Frame für visuelle Embeddings
                first_frame = frames[0]
                
                # Hier könnten verschiedene Embedding-Modelle verwendet werden:
                # - CLIP für visuelle Embeddings
                # - FaceNet für Gesichts-Embeddings
                # - Custom CNN für Video-spezifische Embeddings
                
                # Placeholder für visuelle Embeddings (768-dim CLIP-like)
                visual_embedding = np.random.randn(768).astype(np.float32)
                embeddings['visual'] = visual_embedding
                
                # Audio Embeddings (falls Audio vorhanden)
                if hasattr(self, 'audio_extractor'):
                    audio_features = self.audio_extractor.extract_features(first_frame['path'])
                    if audio_features:
                        # Placeholder für Audio Embeddings (512-dim)
                        audio_embedding = np.random.randn(512).astype(np.float32)
                        embeddings['audio'] = audio_embedding
                
                logger.info(f"✅ Generated {len(embeddings)} embeddings for segment {segment.segment_id}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings for segment {segment.segment_id}: {e}")
            return {}
    
    def get_memory_requirements(self) -> Dict[str, int]:
        """
        Gibt Speicheranforderungen für verschiedene Modelle zurück
        """
        return {
            'base_analyzer': 512 * 1024 * 1024,  # 512MB für Basis-Funktionalität
            'gpt5_vision': 1024 * 1024 * 1024,  # 1GB für GPT-5 Vision
            'scene_detector': 256 * 1024 * 1024,  # 256MB für Scene Detection
            'object_tracker': 512 * 1024 * 1024,  # 512MB für Object Tracking
            'pose_estimator': 1024 * 1024 * 1024, # 1GB für Pose Estimation
            'depth_estimator': 1024 * 1024 * 1024, # 1GB für Depth Estimation
            'total_estimated': 4 * 1024 * 1024 * 1024  # 4GB Gesamtschätzung
        }
    
    def validate_file(self, file_path: str) -> bool:
        """Validate video file"""
        try:
            if not os.path.exists(file_path):
                return False
            
            # Check if it's a video file
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return False
            
            # Check if we can read at least one frame
            ret, frame = cap.read()
            cap.release()
            
            return ret and frame is not None
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False
    
    def create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'status': 'error',
            'error': error_message,
            'segments': [],
            'features': [],
            'embeddings': {},
            'metadata': {
                'analyzer': 'enhanced_video_analyzer',
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def create_success_result(self, segments: List[Dict[str, Any]], features: List[Dict[str, Any]], 
                           embeddings: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create success result"""
        return {
            'status': 'success',
            'segments': segments,
            'features': features,
            'embeddings': embeddings,
            'metadata': {
                **metadata,
                'analyzer': 'enhanced_video_analyzer',
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def log_analysis_start(self, file_path: str, asset_data: Dict[str, Any]):
        """Log analysis start"""
        logger.info(f"🎬 Starting video analysis: {os.path.basename(file_path)}")
    
    def log_analysis_end(self, file_path: str, result: Dict[str, Any]):
        """Log analysis end"""
        status = result.get('status', 'unknown')
        logger.info(f"✅ Video analysis completed: {os.path.basename(file_path)} - Status: {status}")
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis method compatible with the analysis service"""
        self.log_analysis_start(file_path, asset_data)
        
        try:
            if not self.validate_file(file_path):
                return self.create_error_result("Invalid video file")
            
            # Extract segments (scenes)
            segments = await self.extract_segments(file_path)
            logger.info(f"📊 Extracted {len(segments)} segments")
            
            # Create segment dictionaries for database storage
            segment_dicts = []
            all_features = []
            
            for i, segment in enumerate(segments):
                # Create segment dict for database
                segment_dict = {
                    'segment_id': segment.segment_id,
                    'type': 'scene',  # All segments are scenes
                    'sequence_number': i,
                    'start_marker': {'time': segment.start_time},
                    'end_marker': {'time': segment.end_time},
                    'duration': segment.duration,
                    'confidence': 0.8,  # Default confidence for scenes
                    'features': [],
                    'metadata': segment.metadata
                }
                segment_dicts.append(segment_dict)
                
                # Add scene-level features
                scene_features = [
                    {
                        'type': 'scene_detection',
                        'domain': 'visual',
                        'confidence': 0.8,
                        'data': {
                            'scene_id': segment.segment_id,
                            'start_time': segment.start_time,
                            'end_time': segment.end_time,
                            'duration': segment.duration,
                            'scene_index': i
                        },
                        'metadata': {'analyzer': 'enhanced_video_analyzer'}
                    }
                ]
                all_features.extend(scene_features)
            
            # Add overall video features
            overall_features = [
                {
                    'type': 'video_technical',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': {
                        'total_scenes': len(segments),
                        'total_duration': sum(s.duration for s in segments),
                        'analyzer': 'enhanced_video_analyzer'
                    },
                    'metadata': {'analyzer': 'enhanced_video_analyzer'}
                },
                {
                    'type': 'video_scene_analysis',
                    'domain': 'visual',
                    'confidence': 0.85,
                    'data': {
                        'scene_count': len(segments),
                        'average_scene_duration': sum(s.duration for s in segments) / len(segments) if segments else 0,
                        'analyzer': 'enhanced_video_analyzer'
                    },
                    'metadata': {'analyzer': 'enhanced_video_analyzer'}
                }
            ]
            all_features.extend(overall_features)
            
            result = self.create_success_result(
                segments=segment_dicts,
                features=all_features,
                embeddings={},
                metadata={
                    'total_segments': len(segments),
                    'file_path': file_path,
                    'asset_data': asset_data
                }
            )
            
            self.log_analysis_end(file_path, result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Video analysis failed: {e}")
            return self.create_error_result(str(e))
    
    def _extract_frames_from_segment(self, segment: Segment) -> List[Dict[str, Any]]:
        """
        Extrahiert repräsentative Frames aus einem Video-Segment
        """
        try:
            import cv2
            import tempfile
            import os
            
            frames = []
            
            # Öffne Video
            cap = cv2.VideoCapture(segment.metadata.get('video_path', ''))
            if not cap.isOpened():
                return frames
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            start_frame = int(segment.start_time * fps)
            end_frame = int(segment.end_time * fps)
            
            # Extrahiere Frames in regelmäßigen Abständen
            frame_interval = max(1, (end_frame - start_frame) // 5)  # Max 5 Frames pro Segment
            
            for frame_num in range(start_frame, end_frame, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    # Speichere Frame temporär
                    timestamp = frame_num / fps
                    temp_path = f"/tmp/frame_{segment.segment_id}_{frame_num}.jpg"
                    cv2.imwrite(temp_path, frame)
                    
                    frames.append({
                        'path': temp_path,
                        'timestamp': timestamp,
                        'frame_number': frame_num
                    })
            
            cap.release()
            return frames
            
        except Exception as e:
            logger.error(f"❌ Failed to extract frames from segment: {e}")
            return []
    
    def _analyze_frame_cv(self, frame_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Traditionelle Computer Vision Analyse eines Frames
        """
        try:
            import cv2
            
            features = []
            frame_path = frame_data['path']
            
            # Lade Frame
            frame = cv2.imread(frame_path)
            if frame is None:
                return features
            
            # Grundlegende CV-Analysen
            height, width = frame.shape[:2]
            
            # Farbanalyse
            mean_color = np.mean(frame, axis=(0, 1))
            features.append({
                'type': 'color_analysis',
                'frame_time': frame_data['timestamp'],
                'confidence': 0.8,
                'data': {
                    'mean_color_bgr': mean_color.tolist(),
                    'brightness': np.mean(mean_color),
                    'contrast': np.std(frame)
                },
                'metadata': {'analyzer': 'opencv'}
            })
            
            # Objekterkennung (falls YOLO verfügbar)
            if hasattr(self, 'model_manager'):
                # Placeholder für YOLO-Integration
                features.append({
                    'type': 'object_detection',
                    'frame_time': frame_data['timestamp'],
                    'confidence': 0.7,
                    'data': {
                        'objects_detected': 0,  # Placeholder
                        'bounding_boxes': []
                    },
                    'metadata': {'analyzer': 'yolo'}
                })
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze frame with CV: {e}")
            return []
    
    async def analyze_OLD_FRAME_BASED(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """OLD FRAME-BASED METHOD - DEACTIVATED - Comprehensive video analysis with parallel processing"""
        start_time = time.time()
        logger.info(f"Starting enhanced video analysis for {file_path}")
        
        try:
            if not self.validate_file(file_path):
                return self.create_error_result("Invalid video file")
            
            # Get basic video information
            video_info = await self._get_video_info(file_path)
            
            # Use frame storage manager for cleanup
            with FrameStorageManager() as frame_manager:
                # Step 1: Scene Detection
                logger.info("🎬 Starting scene detection...")
                scene_detection_result = await self.scene_detector.detect_scenes(file_path)
                scenes = scene_detection_result.scenes
                logger.info(f"✅ Detected {len(scenes)} scenes")
                
                # Step 2: Frame Extraction
                logger.info("🖼️ Starting frame extraction...")
                extracted_frames = frame_manager.extract_frames_from_scenes(file_path, scenes)
                logger.info(f"✅ Extracted {len(extracted_frames)} frames")
                
                # Step 3: Parallel Analysis Pipeline
                logger.info("🔍 Starting parallel analysis pipeline...")
                
                # Create analysis tasks
                tasks = []
                
                # Audio analysis (parallel to frame analysis)
                if self.config.enable_audio_analysis:
                    tasks.append(self._analyze_audio_task(file_path))
                
                # Frame analysis in batches
                frame_analysis_tasks = self._create_frame_analysis_tasks(extracted_frames, asset_data)
                tasks.extend(frame_analysis_tasks)
                
                # Execute all tasks in parallel
                logger.info(f"🚀 Executing {len(tasks)} analysis tasks in parallel...")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                audio_analysis = None
                frame_analyses = []
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Analysis task {i} failed: {result}")
                        continue
                    
                    if isinstance(result, dict):
                        if result.get('type') == 'audio_analysis':
                            audio_analysis = result
                        elif result.get('type') == 'frame_batch_analysis':
                            # Extract individual frame analyses from batch
                            batch_frames = result.get('frames', [])
                            frame_analyses.extend(batch_frames)
                            logger.info(f"Processed batch: {result.get('successful_analyses', 0)}/{result.get('batch_size', 0)} frames")
                
                logger.info(f"✅ Completed analysis: {len(frame_analyses)} frames, audio: {audio_analysis is not None}")
                
                # Step 4: Enhanced Analysis Pipeline
                logger.info("🚀 Starting enhanced analysis pipeline...")
                
                # Object Tracking
                object_tracking_result = None
                if hasattr(self, 'object_tracker') and frame_analyses:
                    logger.info("🎯 Starting object tracking...")
                    object_tracking_result = await self._analyze_object_tracking(extracted_frames, frame_analyses)
                    logger.info("✅ Object tracking completed")
                
                # Action Recognition
                action_recognition_result = None
                if hasattr(self, 'action_recognizer') and frame_analyses:
                    logger.info("🏃 Starting action recognition...")
                    action_recognition_result = await self._analyze_action_recognition(extracted_frames, frame_analyses)
                    logger.info("✅ Action recognition completed")
                
                # Pose Estimation (Pro-Tier only)
                pose_estimation_result = None
                if hasattr(self, 'pose_estimator') and frame_analyses:
                    logger.info("🧍 Starting pose estimation...")
                    pose_estimation_result = await self._analyze_pose_estimation(extracted_frames)
                    logger.info("✅ Pose estimation completed")
                
                # Depth Estimation (Pro-Tier only)
                depth_estimation_result = None
                if hasattr(self, 'depth_estimator') and frame_analyses:
                    logger.info("📏 Starting depth estimation...")
                    depth_estimation_result = await self._analyze_depth_estimation(extracted_frames)
                    logger.info("✅ Depth estimation completed")
                
                # Quality Assessment
                quality_assessment_result = None
                if hasattr(self, 'quality_analyzer'):
                    logger.info("📊 Starting quality assessment...")
                    quality_assessment_result = await self._analyze_quality(file_path)
                    logger.info("✅ Quality assessment completed")
                
                # Safety Analysis
                safety_analysis_result = None
                if hasattr(self, 'safety_analyzer') and frame_analyses:
                    logger.info("🛡️ Starting safety analysis...")
                    safety_analysis_result = await self._analyze_safety(extracted_frames)
                    logger.info("✅ Safety analysis completed")
                
                # Temporal Analysis (existing)
                temporal_analysis = None
                if self.config.enable_movement_tracking and frame_analyses:
                    logger.info("⏱️ Starting temporal analysis...")
                    temporal_analysis = await self._analyze_temporal_patterns(frame_analyses)
                    logger.info("✅ Temporal analysis completed")
                
                # Step 5: Build Hierarchical Result
                logger.info("🏗️ Building hierarchical result...")
                video_result = self.result_builder.build_video_result(
                    video_path=file_path,
                    video_info=video_info,
                    scene_detection_result=scene_detection_result.to_dict(),
                    frame_analyses=frame_analyses,
                    audio_analysis=audio_analysis,
                    temporal_analysis=temporal_analysis,
                    # Enhanced analysis results
                    object_tracking_result=object_tracking_result,
                    action_recognition_result=action_recognition_result,
                    pose_estimation_result=pose_estimation_result,
                    depth_estimation_result=depth_estimation_result,
                    quality_assessment_result=quality_assessment_result,
                    safety_analysis_result=safety_analysis_result
                )
                
                # Step 6: Video Summarization (if enabled)
                video_summary = None
                if hasattr(self, 'video_summarizer'):
                    logger.info("📝 Starting video summarization...")
                    try:
                        # Prepare analysis data for summarization
                        analysis_data = {
                            'duration': video_info.get('duration', 0),
                            'scenes': scene_detection_result.to_dict().get('scenes', []),
                            'frame_analyses': frame_analyses,
                            'features': [],  # Will be populated from video_result
                            'embeddings': []  # Will be populated from video_result
                        }
                        
                        video_summary = await self.video_summarizer.generate_summary(analysis_data)
                        logger.info("✅ Video summarization completed")
                    except Exception as e:
                        logger.error(f"Video summarization failed: {e}")
                
                # Step 7: Convert to standard format
                result = self._convert_to_standard_format(video_result, video_summary)
                
                processing_time = time.time() - start_time
                log_memory_stats("EnhancedVideoAnalyzer completion")
                logger.info(f"🎉 Enhanced video analysis completed in {processing_time:.2f}s")
                
                return result
                
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return self.create_error_result(str(e))
    
    async def _get_video_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic video information"""
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {file_path}")
            
            info = {
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0,
                'codec': int(cap.get(cv2.CAP_PROP_FOURCC))
            }
            
            cap.release()
            return info
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}
    
    async def _analyze_audio_task(self, video_path: str) -> Dict[str, Any]:
        """Audio analysis task"""
        try:
            audio_result = await self.audio_extractor.extract_audio(video_path)
            return {
                'type': 'audio_analysis',
                'data': audio_result.to_dict()
            }
        except Exception as e:
            logger.error(f"Audio analysis task failed: {e}")
            return {'type': 'audio_analysis', 'error': str(e)}
    
    def _create_frame_analysis_tasks(self, extracted_frames: List[FrameData], asset_data: Dict[str, Any]) -> List:
        """Create frame analysis tasks in batches"""
        tasks = []
        
        # Process frames in batches
        batch_size = self.config.batch_size
        for i in range(0, len(extracted_frames), batch_size):
            batch = extracted_frames[i:i + batch_size]
            task = self._analyze_frame_batch(batch, asset_data)
            tasks.append(task)
        
        return tasks
    
    async def _analyze_frame_batch(self, frame_batch: List[FrameData], asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a batch of frames"""
        batch_results = []
        
        for frame_data in frame_batch:
            try:
                # Prepare frame context for ImageAnalyzer
                frame_context = {
                    'is_keyframe': frame_data.timestamp % self.config.frame_sampling_rate < 0.1,
                    'is_scene_boundary': frame_data.metadata.get('is_scene_boundary', False),
                    'scene_id': frame_data.scene_id,
                    'timestamp': frame_data.timestamp
                }
                
                # Create asset data with frame context
                frame_asset_data = asset_data.copy()
                frame_asset_data['frame_context'] = frame_context
                
                # Analyze frame with ImageAnalyzer
                frame_analysis = await self.image_analyzer.analyze(
                    frame_data.image_path, 
                    frame_asset_data
                )
                
                # Add frame metadata
                frame_result = {
                    'type': 'frame_analysis',
                    'frame_id': frame_data.frame_id,
                    'scene_id': frame_data.scene_id,
                    'timestamp': frame_data.timestamp,
                    'frame_index': frame_data.frame_index,
                    'image_path': frame_data.image_path,
                    'thumbnail_path': frame_data.thumbnail_path,
                    'features': frame_analysis.get('features', []),
                    'embeddings': frame_analysis.get('embeddings', []),
                    'confidence': 0.9
                }
                
                batch_results.append(frame_result)
                
            except Exception as e:
                logger.error(f"Frame analysis failed for frame {frame_data.frame_id}: {e}")
                continue
        
        return {
            'type': 'frame_batch_analysis',
            'frames': batch_results,
            'batch_size': len(frame_batch),
            'successful_analyses': len(batch_results)
        }
    
    async def _analyze_temporal_patterns(self, frame_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns across frames"""
        try:
            # Group frames by scene
            scene_frames = {}
            for frame in frame_analyses:
                scene_id = frame.get('scene_id', 0)
                if scene_id not in scene_frames:
                    scene_frames[scene_id] = []
                scene_frames[scene_id].append(frame)
            
            # Analyze movement patterns
            movement_patterns = []
            for scene_id, frames in scene_frames.items():
                if len(frames) > 1:
                    # Simple movement analysis based on object detection changes
                    movement_score = self._calculate_scene_movement(frames)
                    movement_patterns.append({
                        'scene_id': scene_id,
                        'movement_score': movement_score,
                        'frame_count': len(frames)
                    })
            
            return {
                'movement_patterns': movement_patterns,
                'total_scenes_analyzed': len(scene_frames),
                'average_movement_score': np.mean([p['movement_score'] for p in movement_patterns]) if movement_patterns else 0
            }
            
        except Exception as e:
            logger.error(f"Temporal analysis failed: {e}")
            return {'error': str(e)}
    
    def _calculate_scene_movement(self, frames: List[Dict[str, Any]]) -> float:
        """Calculate movement score for a scene"""
        try:
            # Extract object counts from frames
            object_counts = []
            for frame in frames:
                features = frame.get('features', [])
                for feature in features:
                    if feature.get('type') == 'object_detection':
                        objects = feature.get('data', {}).get('objects', [])
                        object_counts.append(len(objects))
                        break
                else:
                    object_counts.append(0)
            
            if len(object_counts) < 2:
                return 0.0
            
            # Calculate variance in object counts as movement indicator
            movement_score = np.var(object_counts) / (np.mean(object_counts) + 1)
            return min(movement_score, 1.0)
            
        except Exception as e:
            logger.error(f"Movement calculation failed: {e}")
            return 0.0
    
    # Enhanced Analysis Methods
    
    async def _analyze_object_tracking(self, extracted_frames: List[FrameData], frame_analyses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Analyze object tracking across frames"""
        try:
            # Extract frames and detections for tracking
            scene_frames = []
            scene_detections = []
            
            for frame_data in extracted_frames:
                # Load frame
                frame = cv2.imread(str(frame_data.image_path))
                if frame is not None:
                    scene_frames.append(frame)
                    
                    # Find corresponding frame analysis
                    frame_analysis = next(
                        (fa for fa in frame_analyses if fa.get('frame_id') == frame_data.frame_id), 
                        None
                    )
                    
                    if frame_analysis:
                        # Extract detections
                        detections = []
                        for feature in frame_analysis.get('features', []):
                            if feature.get('type') == 'object_detection':
                                objects = feature.get('data', {}).get('objects', [])
                                for obj in objects:
                                    detections.append({
                                        'bbox': obj.get('bbox', [0, 0, 0, 0]),
                                        'confidence': obj.get('confidence', 0.0),
                                        'class_id': obj.get('class_id', 0),
                                        'class_name': obj.get('class_name', 'unknown')
                                    })
                        scene_detections.append(detections)
                    else:
                        scene_detections.append([])
            
            if scene_frames:
                # Initialize tracker if needed
                await self.object_tracker.initialize_tracker()
                
                # Track objects in scene
                tracking_result = await self.object_tracker.track_objects_in_scene(
                    scene_frames, scene_detections
                )
                
                return {
                    'type': 'object_tracking',
                    'data': {
                        'tracked_objects': [
                            {
                                'track_id': obj.track_id,
                                'class_name': obj.class_name,
                                'trajectory': obj.trajectory,
                                'velocity': obj.velocity,
                                'age': obj.age
                            }
                            for obj in tracking_result.tracked_objects
                        ],
                        'movement_stats': tracking_result.movement_stats,
                        'scene_movement_score': tracking_result.scene_movement_score
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Object tracking analysis failed: {e}")
            return None
    
    async def _analyze_action_recognition(self, extracted_frames: List[FrameData], frame_analyses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Analyze actions in frames"""
        try:
            # Extract frames for action recognition
            scene_frames = []
            timestamps = []
            
            for frame_data in extracted_frames:
                frame = cv2.imread(str(frame_data.image_path))
                if frame is not None:
                    scene_frames.append(frame)
                    timestamps.append(frame_data.timestamp)
            
            if scene_frames:
                # Initialize action recognizer if needed
                await self.action_recognizer.initialize_model()
                
                # Recognize actions in scene
                action_result = await self.action_recognizer.recognize_actions_in_scene(
                    scene_frames, timestamps=timestamps
                )
                
                return {
                    'type': 'action_recognition',
                    'data': {
                        'actions': [
                            {
                                'action_name': action.action_name,
                                'confidence': action.confidence,
                                'context': action.context,
                                'timestamp': action.timestamp
                            }
                            for action in action_result.actions
                        ],
                        'scene_activities': action_result.scene_activities,
                        'dominant_activity': action_result.dominant_activity,
                        'confidence_score': action_result.confidence_score
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Action recognition analysis failed: {e}")
            return None
    
    async def _analyze_pose_estimation(self, extracted_frames: List[FrameData]) -> Optional[Dict[str, Any]]:
        """Analyze poses in frames (Pro-Tier only)"""
        try:
            # Extract frames for pose estimation
            scene_frames = []
            timestamps = []
            
            for frame_data in extracted_frames:
                frame = cv2.imread(str(frame_data.image_path))
                if frame is not None:
                    scene_frames.append(frame)
                    timestamps.append(frame_data.timestamp)
            
            if scene_frames:
                # Initialize pose estimator if needed
                await self.pose_estimator.initialize_model()
                
                # Estimate poses in scene
                pose_result = await self.pose_estimator.estimate_poses_in_scene(
                    scene_frames, timestamps=timestamps
                )
                
                return {
                    'type': 'pose_estimation',
                    'data': {
                        'poses': [
                            {
                                'person_id': pose.person_id,
                                'pose_classification': pose.pose_classification,
                                'confidence': pose.confidence,
                                'body_landmarks_count': len(pose.body_landmarks),
                                'has_hands': pose.left_hand_landmarks is not None or pose.right_hand_landmarks is not None,
                                'has_face': pose.face_landmarks is not None
                            }
                            for pose in pose_result.poses
                        ],
                        'scene_summary': pose_result.scene_pose_summary,
                        'dominant_poses': pose_result.dominant_poses
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Pose estimation analysis failed: {e}")
            return None
    
    async def _analyze_depth_estimation(self, extracted_frames: List[FrameData]) -> Optional[Dict[str, Any]]:
        """Analyze depth in frames (Pro-Tier only)"""
        try:
            # Extract frames for depth estimation
            scene_frames = []
            
            for frame_data in extracted_frames:
                frame = cv2.imread(str(frame_data.image_path))
                if frame is not None:
                    scene_frames.append(frame)
            
            if scene_frames:
                # Initialize depth estimator if needed
                await self.depth_estimator.initialize_model()
                
                # Estimate depth in scene
                depth_result = await self.depth_estimator.estimate_depth_in_scene(scene_frames)
                
                return {
                    'type': 'depth_estimation',
                    'data': {
                        'depth_maps_count': len(depth_result.depth_maps),
                        'scene_summary': depth_result.scene_depth_summary,
                        'foreground_objects': depth_result.foreground_objects,
                        'background_regions': depth_result.background_regions,
                        'has_visualization': depth_result.depth_visualization is not None
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Depth estimation analysis failed: {e}")
            return None
    
    async def _analyze_quality(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Analyze video quality"""
        try:
            quality_result = await self.quality_analyzer.analyze_video_quality(video_path)
            
            return {
                'type': 'quality_assessment',
                'data': {
                    'video_quality': {
                        'resolution': quality_result.video_quality.resolution,
                        'fps': quality_result.video_quality.fps,
                        'overall_score': quality_result.video_quality.overall_quality_score
                    },
                    'camera_motion': {
                        'motion_type': quality_result.camera_motion.motion_type,
                        'stability_score': quality_result.camera_motion.stability_score,
                        'pan_speed': quality_result.camera_motion.pan_speed,
                        'tilt_speed': quality_result.camera_motion.tilt_speed
                    },
                    'lighting': {
                        'brightness_level': quality_result.lighting.brightness_level,
                        'contrast_level': quality_result.lighting.contrast_level,
                        'quality_score': quality_result.lighting.lighting_quality_score
                    },
                    'overall_quality_score': quality_result.overall_quality_score,
                    'recommendations': quality_result.recommendations
                }
            }
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return None
    
    async def _analyze_safety(self, extracted_frames: List[FrameData]) -> Optional[Dict[str, Any]]:
        """Analyze content safety"""
        try:
            # Extract frames for safety analysis
            scene_frames = []
            timestamps = []
            
            for frame_data in extracted_frames:
                frame = cv2.imread(str(frame_data.image_path))
                if frame is not None:
                    scene_frames.append(frame)
                    timestamps.append(frame_data.timestamp)
            
            if scene_frames:
                # Initialize safety analyzer if needed
                await self.safety_analyzer.initialize_models()
                
                # Analyze safety in scene
                safety_result = await self.safety_analyzer.analyze_safety_in_scene(
                    scene_frames, timestamps=timestamps
                )
                
                return {
                    'type': 'safety_analysis',
                    'data': {
                        'overall_safety_score': safety_result.overall_safety_score,
                        'is_safe_for_work': safety_result.is_safe_for_work,
                        'requires_age_restriction': safety_result.requires_age_restriction,
                        'content_warnings': safety_result.content_warnings,
                        'recommended_actions': safety_result.recommended_actions,
                        'detections': [
                            {
                                'detection_type': detection.detection_type,
                                'confidence': detection.confidence,
                                'severity': detection.severity,
                                'description': detection.description
                            }
                            for detection in safety_result.safety_detections
                        ]
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Safety analysis failed: {e}")
            return None

    def _convert_to_standard_format(self, video_result, video_summary=None) -> Dict[str, Any]:
        """Convert hierarchical result to standard analyzer format"""
        # Flatten segments and ensure correct type field
        segments = []
        
        # Add scene segments with correct type and all required fields
        for i, scene in enumerate(video_result.scenes):
            scene_segment = {
                'segment_id': scene.get('segment_id', f'scene_{i}'),
                'type': 'scene',
                'sequence_number': i,
                'start_marker': scene.get('start_marker', {'time': 0.0}),
                'end_marker': scene.get('end_marker', {'time': 0.0}),
                'duration': scene.get('duration', 1.0),
                'confidence': scene.get('confidence_score', 0.8),
                'features': scene.get('features', []),
                'metadata': scene.get('metadata', {})
            }
            segments.append(scene_segment)
        
        # Don't add frame segments - they should be features within scenes
        # Frames are already included in scene features
        
        # Combine all features
        features = video_result.overall_features.copy()
        for scene in video_result.scenes:
            features.extend(scene.get('features', []))
        for frame in video_result.frame_analyses:
            features.extend(frame.get('features', []))
        
        # Combine all embeddings
        embeddings = video_result.overall_embeddings.copy()
        for frame in video_result.frame_analyses:
            embeddings.extend(frame.get('embeddings', []))
        
        # Add enhanced features to metadata
        enhanced_metadata = {
            'video_metadata': video_result.video_metadata,
            'audio_analysis': video_result.audio_analysis,
            'temporal_analysis': video_result.temporal_analysis,
            'total_scenes': len(video_result.scenes),
            'total_frames': len(video_result.frame_analyses),
            'analyzer_version': 'enhanced_video_analyzer_v2.0',
            'tier_used': self.model_manager.get_current_tier(),
            'enhanced_features': {
                'object_tracking': hasattr(self, 'object_tracker'),
                'action_recognition': hasattr(self, 'action_recognizer'),
                'pose_estimation': hasattr(self, 'pose_estimator'),
                'depth_estimation': hasattr(self, 'depth_estimator'),
                'quality_assessment': hasattr(self, 'quality_analyzer'),
                'safety_analysis': hasattr(self, 'safety_analyzer'),
                'video_summarization': hasattr(self, 'video_summarizer')
            }
        }
        
        # Add video summary if available
        if video_summary:
            enhanced_metadata['video_summary'] = {
                'brief_summary': video_summary.brief_summary,
                'detailed_summary': video_summary.detailed_summary,
                'keywords': video_summary.keywords,
                'topics': video_summary.topics,
                'sentiment': video_summary.sentiment,
                'confidence': video_summary.confidence,
                'llm_used': video_summary.llm_used
            }
        
        # Create success result as dictionary
        result = {
            'scenes': segments,
            'features': features,
            'embeddings': embeddings,
            'duration': video_result.duration if hasattr(video_result, 'duration') else 0.0,
            'error': None
        }
        
        return result
    
# Legacy VideoAnalyzer class for backward compatibility
class VideoAnalyzer(EnhancedVideoAnalyzer):
    """Legacy video analyzer - now uses EnhancedVideoAnalyzer"""
    
    def __init__(self):
        super().__init__()
        logger.info("Using Enhanced Video Analyzer (legacy compatibility mode)")
