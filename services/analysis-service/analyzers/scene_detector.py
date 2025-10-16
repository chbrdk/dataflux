"""
Advanced Scene Detection Module
Implements intelligent scene detection using PySceneDetect with multiple algorithms
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from pathlib import Path

try:
    from scenedetect import detect, ContentDetector, AdaptiveDetector, ThresholdDetector
    from scenedetect.video_manager import VideoManager
    from scenedetect.scene_manager import SceneManager
    from scenedetect.frame_timecode import FrameTimecode
    SCENEDETECT_AVAILABLE = True
except ImportError:
    SCENEDETECT_AVAILABLE = False

from .video_config import get_video_config, SceneDetectionMethod

logger = logging.getLogger(__name__)

class SceneDetectionResult:
    """Container for scene detection results"""
    
    def __init__(self, 
                 scenes: List[Dict[str, Any]],
                 detection_method: str,
                 confidence: float,
                 metadata: Optional[Dict[str, Any]] = None):
        self.scenes = scenes
        self.detection_method = detection_method
        self.confidence = confidence
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'scenes': self.scenes,
            'detection_method': self.detection_method,
            'confidence': self.confidence,
            'metadata': self.metadata
        }

class AdvancedSceneDetector:
    """Advanced scene detection using PySceneDetect"""
    
    def __init__(self):
        self.config = get_video_config()
        self.scenedetect_available = SCENEDETECT_AVAILABLE
        
        if not self.scenedetect_available:
            logger.warning("PySceneDetect not available, falling back to OpenCV-based detection")
    
    async def detect_scenes(self, video_path: str) -> SceneDetectionResult:
        """Detect scenes in video using configured method"""
        try:
            if self.scenedetect_available:
                return await self._detect_scenes_scenedetect(video_path)
            else:
                return await self._detect_scenes_opencv(video_path)
                
        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            # Fallback to basic detection
            return await self._detect_scenes_basic(video_path)
    
    async def _detect_scenes_scenedetect(self, video_path: str) -> SceneDetectionResult:
        """Detect scenes using PySceneDetect"""
        try:
            logger.info(f"Starting PySceneDetect scene detection for {video_path}")
            
            # Try multiple thresholds to find scenes
            thresholds = [15.0, 10.0, 5.0, 2.0]  # Try progressively lower thresholds
            scenes = []
            
            for threshold in thresholds:
                logger.info(f"Trying threshold {threshold}")
                try:
                    scene_list = detect(
                        video_path,
                        ContentDetector(threshold=threshold),
                        show_progress=False
                    )
                    
                    logger.info(f"PySceneDetect found {len(scene_list)} scenes with threshold {threshold}")
                    
                    # Convert to our format
                    scenes = []
                    for i, (start_time, end_time) in enumerate(scene_list):
                        scenes.append({
                            'scene_id': i,
                            'start_time': start_time.get_seconds(),
                            'end_time': end_time.get_seconds(),
                            'duration': end_time.get_seconds() - start_time.get_seconds(),
                            'start_frame': start_time.get_frames(),
                            'end_frame': end_time.get_frames(),
                            'confidence': 0.9,
                            'detection_method': f'scenedetect_threshold_{threshold}'
                        })
                    
                    # If we found more than 1 scene, use this result
                    if len(scenes) > 1:
                        logger.info(f"Found {len(scenes)} scenes with threshold {threshold}")
                        break
                except Exception as e:
                    logger.error(f"PySceneDetect failed with threshold {threshold}: {e}")
                    continue
            
            # If still no scenes detected, create a single scene for the entire video
            if not scenes:
                logger.warning("No scenes detected with any threshold, creating single scene for entire video")
                # Get video duration
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                
                scenes = [{
                    'scene_id': 0,
                    'start_time': 0.0,
                    'end_time': duration,
                    'duration': duration,
                    'start_frame': 0,
                    'end_frame': frame_count,
                    'confidence': 0.5,
                    'detection_method': 'scenedetect_fallback'
                }]
            
            # Calculate overall confidence
            confidence = self._calculate_detection_confidence(scenes)
            
            metadata = {
                'total_scenes': len(scenes),
                'video_duration': scenes[-1]['end_time'] if scenes else 0,
                'average_scene_length': np.mean([s['duration'] for s in scenes]) if scenes else 0,
                'detectors_used': ['ContentDetector']
            }
            
            logger.info(f"PySceneDetect found {len(scenes)} scenes")
            return SceneDetectionResult(
                scenes=scenes,
                detection_method='scenedetect',
                confidence=confidence,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"PySceneDetect detection failed: {e}")
            raise
    
    def _create_detectors(self) -> List:
        """Create detectors based on configuration"""
        detectors = []
        
        if self.config.scene_detection_method == SceneDetectionMethod.CONTENT_DETECTOR:
            detectors.append(ContentDetector(threshold=self.config.content_threshold))
        
        elif self.config.scene_detection_method == SceneDetectionMethod.ADAPTIVE_DETECTOR:
            detectors.append(AdaptiveDetector(adaptive_threshold=self.config.adaptive_threshold))
        
        elif self.config.scene_detection_method == SceneDetectionMethod.THRESHOLD_DETECTOR:
            detectors.append(ThresholdDetector(threshold=self.config.content_threshold))
        
        elif self.config.scene_detection_method == SceneDetectionMethod.COMBINED:
            # Use multiple detectors for better accuracy
            detectors.append(ContentDetector(threshold=self.config.content_threshold))
            detectors.append(AdaptiveDetector(adaptive_threshold=self.config.adaptive_threshold))
        
        return detectors
    
    async def _detect_scenes_opencv(self, video_path: str) -> SceneDetectionResult:
        """Fallback scene detection using OpenCV with aggressive thresholds"""
        try:
            logger.info(f"Starting OpenCV scene detection for {video_path}")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            logger.info(f"Video info: {frame_count} frames, {fps} fps, {duration:.2f}s duration")
            
            # Try multiple thresholds to find scenes
            thresholds = [30.0, 20.0, 15.0, 10.0, 5.0]
            best_scenes = []
            
            for threshold in thresholds:
                logger.info(f"Trying OpenCV threshold {threshold}")
                scenes = []
                prev_frame = None
                scene_start = 0
                scene_count = 0
                
                # Sample every second for efficiency
                sample_interval = max(1, int(fps))
                
                for frame_idx in range(0, frame_count, sample_interval):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    
                    if not ret:
                        break
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    if prev_frame is not None:
                        # Calculate frame difference
                        diff = cv2.absdiff(prev_frame, gray)
                        mean_diff = np.mean(diff)
                        
                        if mean_diff > threshold:
                            scene_end = frame_idx / fps
                            scene_duration = scene_end - scene_start
                            
                            # Only create scene if it meets minimum length (1 second)
                            if scene_duration >= 1.0:
                                scenes.append({
                                    'scene_id': scene_count,
                                    'start_time': scene_start,
                                    'end_time': scene_end,
                                    'duration': scene_duration,
                                    'start_frame': int(scene_start * fps),
                                    'end_frame': int(scene_end * fps),
                                    'confidence': min(mean_diff / 100.0, 1.0),
                                    'detection_method': f'opencv_threshold_{threshold}'
                                })
                                
                                scene_start = scene_end
                                scene_count += 1
                    
                    prev_frame = gray
                
                # Add final scene
                if scene_start < duration:
                    final_duration = duration - scene_start
                    if final_duration >= 1.0:
                        scenes.append({
                            'scene_id': scene_count,
                            'start_time': scene_start,
                            'end_time': duration,
                            'duration': final_duration,
                            'start_frame': int(scene_start * fps),
                            'end_frame': frame_count - 1,
                            'confidence': 0.8,
                            'detection_method': f'opencv_threshold_{threshold}'
                        })
                
                logger.info(f"OpenCV found {len(scenes)} scenes with threshold {threshold}")
                
                # If we found more than 1 scene, use this result
                if len(scenes) > 1:
                    best_scenes = scenes
                    logger.info(f"Found {len(scenes)} scenes with threshold {threshold}")
                    break
                elif len(scenes) == 1 and len(best_scenes) == 0:
                    best_scenes = scenes  # Keep single scene as fallback
            
            cap.release()
            
            # If still no scenes, create artificial scenes every 10 seconds
            if len(best_scenes) <= 1 and duration > 10:
                logger.info("Creating artificial scenes every 10 seconds")
                best_scenes = []
                scene_count = 0
                for start_time in np.arange(0, duration, 10):
                    end_time = min(start_time + 10, duration)
                    best_scenes.append({
                        'scene_id': scene_count,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'start_frame': int(start_time * fps),
                        'end_frame': int(end_time * fps),
                        'confidence': 0.3,
                        'detection_method': 'opencv_artificial'
                    })
                    scene_count += 1
            
            confidence = self._calculate_detection_confidence(best_scenes)
            
            metadata = {
                'total_scenes': len(best_scenes),
                'video_duration': duration,
                'average_scene_length': np.mean([s['duration'] for s in best_scenes]) if best_scenes else 0,
                'detectors_used': ['OpenCV']
            }
            
            logger.info(f"OpenCV detected {len(best_scenes)} scenes")
            return SceneDetectionResult(
                scenes=best_scenes,
                detection_method='opencv',
                confidence=confidence,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"OpenCV scene detection failed: {e}")
            raise
    
    async def _detect_scenes_basic(self, video_path: str) -> SceneDetectionResult:
        """Basic scene detection as ultimate fallback"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Create single scene covering entire video
            scenes = [{
                'scene_id': 0,
                'start_time': 0.0,
                'end_time': duration,
                'duration': duration,
                'start_frame': 0,
                'end_frame': frame_count - 1,
                'confidence': 0.5,
                'detection_method': 'basic'
            }]
            
            cap.release()
            
            metadata = {
                'total_scenes': 1,
                'video_duration': duration,
                'fallback_reason': 'advanced_detection_failed'
            }
            
            logger.warning("Using basic scene detection (single scene)")
            return SceneDetectionResult(
                scenes=scenes,
                detection_method='basic',
                confidence=0.5,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Basic scene detection failed: {e}")
            # Return empty result
            return SceneDetectionResult(
                scenes=[],
                detection_method='failed',
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    def _calculate_detection_confidence(self, scenes: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence for scene detection"""
        if not scenes:
            return 0.0
        
        # Base confidence on scene count and distribution
        scene_count = len(scenes)
        durations = [scene['duration'] for scene in scenes]
        
        # Penalize too many or too few scenes
        if scene_count == 1:
            confidence = 0.3  # Single scene is suspicious
        elif scene_count < 3:
            confidence = 0.6
        elif scene_count > 50:
            confidence = 0.4  # Too many scenes
        else:
            confidence = 0.8
        
        # Adjust based on scene length distribution
        if durations:
            avg_duration = np.mean(durations)
            std_duration = np.std(durations)
            
            # Penalize very short scenes or high variance
            if avg_duration < 1.0:
                confidence *= 0.7
            if std_duration > avg_duration:
                confidence *= 0.8
        
        # Adjust based on individual scene confidences
        scene_confidences = [scene.get('confidence', 0.5) for scene in scenes]
        avg_scene_confidence = np.mean(scene_confidences)
        confidence = (confidence + avg_scene_confidence) / 2
        
        return min(confidence, 1.0)
    
    def validate_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean up scene data"""
        validated_scenes = []
        
        for scene in scenes:
            # Ensure required fields
            if not all(key in scene for key in ['start_time', 'end_time', 'scene_id']):
                logger.warning(f"Skipping invalid scene: {scene}")
                continue
            
            # Ensure positive duration
            duration = scene['end_time'] - scene['start_time']
            if duration <= 0:
                logger.warning(f"Skipping scene with invalid duration: {scene}")
                continue
            
            # Ensure minimum scene length
            if duration < self.config.min_scene_length:
                logger.warning(f"Skipping scene shorter than minimum length: {duration}s")
                continue
            
            # Add calculated fields
            scene['duration'] = duration
            scene['confidence'] = scene.get('confidence', 0.8)
            
            validated_scenes.append(scene)
        
        # Re-index scene IDs
        for i, scene in enumerate(validated_scenes):
            scene['scene_id'] = i
        
        logger.info(f"Validated {len(validated_scenes)} scenes")
        return validated_scenes
