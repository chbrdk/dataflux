"""
Enhanced Scene Detector for Video Analysis
Detects scene boundaries and creates scene segments
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SceneSegment:
    """Represents a detected scene segment"""
    scene_id: str
    start_time: float
    end_time: float
    duration: float
    start_frame: int
    end_frame: int
    confidence: float
    metadata: Dict[str, Any]

class EnhancedSceneDetector:
    """Advanced scene detection using multiple methods"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'method': 'histogram_diff',  # histogram_diff, optical_flow, color_space
            'threshold': 0.3,
            'min_scene_duration': 1.0,  # Minimum scene duration in seconds
            'max_scenes': 50,  # Maximum number of scenes
            'smoothing_window': 5
        }
        
        logger.info(f"🎬 Enhanced Scene Detector initialized with method: {self.config['method']}")
    
    def detect_scenes(self, video_path: str) -> List[SceneSegment]:
        """
        Detect scene boundaries in video
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of SceneSegment objects
        """
        try:
            logger.info(f"🎬 Starting scene detection for: {Path(video_path).name}")
            
            # Get video properties
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📊 Video properties: {total_frames} frames, {fps:.2f} FPS, {duration:.2f}s duration")
            
            # Detect scene boundaries based on method
            if self.config['method'] == 'histogram_diff':
                scene_boundaries = self._detect_by_histogram_diff(cap)
            elif self.config['method'] == 'optical_flow':
                scene_boundaries = self._detect_by_optical_flow(cap)
            elif self.config['method'] == 'color_space':
                scene_boundaries = self._detect_by_color_space(cap)
            else:
                # Fallback: single scene
                scene_boundaries = [0, total_frames - 1]
            
            cap.release()
            
            # Convert boundaries to scene segments
            scenes = self._create_scene_segments(scene_boundaries, fps, total_frames)
            
            # Apply post-processing
            scenes = self._post_process_scenes(scenes)
            
            logger.info(f"✅ Detected {len(scenes)} scenes")
            return scenes
            
        except Exception as e:
            logger.error(f"❌ Scene detection failed: {e}")
            # Fallback: return single scene
            return self._create_fallback_scene(video_path)
    
    def _detect_by_histogram_diff(self, cap: cv2.VideoCapture) -> List[int]:
        """Detect scenes using histogram difference"""
        boundaries = [0]
        prev_hist = None
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Calculate histogram
            hist = cv2.calcHist([hsv], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            if prev_hist is not None:
                # Calculate histogram difference
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                
                # If correlation is below threshold, it's a scene boundary
                if diff < self.config['threshold']:
                    boundaries.append(frame_count)
            
            prev_hist = hist
            frame_count += 1
        
        boundaries.append(frame_count - 1)
        return boundaries
    
    def _detect_by_optical_flow(self, cap: cv2.VideoCapture) -> List[int]:
        """Detect scenes using optical flow analysis"""
        boundaries = [0]
        prev_gray = None
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_gray is not None:
                # Calculate optical flow
                flow = cv2.calcOpticalFlowPyrLK(prev_gray, gray, None, None)
                
                # Calculate motion magnitude
                if flow[0] is not None and len(flow[0]) > 0:
                    motion_magnitude = np.mean(np.linalg.norm(flow[1] - flow[0], axis=1))
                    
                    # If motion is high, it might be a scene change
                    if motion_magnitude > self.config['threshold'] * 100:
                        boundaries.append(frame_count)
            
            prev_gray = gray
            frame_count += 1
        
        boundaries.append(frame_count - 1)
        return boundaries
    
    def _detect_by_color_space(self, cap: cv2.VideoCapture) -> List[int]:
        """Detect scenes using color space analysis"""
        boundaries = [0]
        prev_colors = None
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Analyze dominant colors
            pixels = frame.reshape(-1, 3)
            colors = np.mean(pixels, axis=0)
            
            if prev_colors is not None:
                # Calculate color difference
                color_diff = np.linalg.norm(colors - prev_colors)
                
                # If color change is significant, it's a scene boundary
                if color_diff > self.config['threshold'] * 100:
                    boundaries.append(frame_count)
            
            prev_colors = colors
            frame_count += 1
        
        boundaries.append(frame_count - 1)
        return boundaries
    
    def _create_scene_segments(self, boundaries: List[int], fps: float, total_frames: int) -> List[SceneSegment]:
        """Convert frame boundaries to scene segments"""
        scenes = []
        
        for i in range(len(boundaries) - 1):
            start_frame = boundaries[i]
            end_frame = boundaries[i + 1]
            
            # Skip very short scenes
            duration = (end_frame - start_frame) / fps
            if duration < self.config['min_scene_duration']:
                continue
            
            scene = SceneSegment(
                scene_id=f"scene_{i:03d}",
                start_time=start_frame / fps,
                end_time=end_frame / fps,
                duration=duration,
                start_frame=start_frame,
                end_frame=end_frame,
                confidence=0.8,  # Default confidence
                metadata={
                    'fps': fps,
                    'total_frames': total_frames,
                    'scene_index': i,
                    'detection_method': self.config['method']
                }
            )
            scenes.append(scene)
        
        return scenes
    
    def _post_process_scenes(self, scenes: List[SceneSegment]) -> List[SceneSegment]:
        """Apply post-processing to detected scenes"""
        if not scenes:
            return scenes
        
        # Limit number of scenes
        if len(scenes) > self.config['max_scenes']:
            # Keep the longest scenes
            scenes.sort(key=lambda x: x.duration, reverse=True)
            scenes = scenes[:self.config['max_scenes']]
            scenes.sort(key=lambda x: x.start_time)
        
        # Smooth scene boundaries
        for i in range(1, len(scenes)):
            prev_scene = scenes[i - 1]
            curr_scene = scenes[i]
            
            # If scenes are too close, merge them
            if curr_scene.start_time - prev_scene.end_time < 0.5:
                prev_scene.end_time = curr_scene.end_time
                prev_scene.duration = prev_scene.end_time - prev_scene.start_time
                prev_scene.end_frame = curr_scene.end_frame
                scenes.pop(i)
                break
        
        return scenes
    
    def _create_fallback_scene(self, video_path: str) -> List[SceneSegment]:
        """Create a fallback single scene if detection fails"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        duration = total_frames / fps if fps > 0 else 0
        
        return [SceneSegment(
            scene_id="scene_000",
            start_time=0.0,
            end_time=duration,
            duration=duration,
            start_frame=0,
            end_frame=total_frames - 1,
            confidence=0.5,
            metadata={
                'fps': fps,
                'total_frames': total_frames,
                'scene_index': 0,
                'detection_method': 'fallback'
            }
        )]

# Factory function
def create_scene_detector(config: Dict[str, Any] = None) -> EnhancedSceneDetector:
    """Create a scene detector instance"""
    return EnhancedSceneDetector(config)
