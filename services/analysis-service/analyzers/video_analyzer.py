"""
Video Analyzer for DataFlux Analysis Service
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
from pathlib import Path

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)

class VideoAnalyzer(BaseAnalyzer):
    """Video content analyzer with scene detection and object recognition"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv',
            'video/webm', 'video/flv', 'video/wmv'
        ]
        
    def get_supported_formats(self) -> List[str]:
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze video file"""
        self.log_analysis_start(file_path, asset_data)
        
        try:
            if not self.validate_file(file_path):
                return self.create_error_result("Invalid file")
            
            # Run analysis tasks in parallel
            tasks = [
                self._detect_scenes(file_path),
                self._extract_frames(file_path),
                self._analyze_audio(file_path),
                self._detect_objects(file_path)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            segments = []
            features = []
            embeddings = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Analysis task {i} failed", error=str(result))
                    continue
                
                if isinstance(result, dict):
                    segments.extend(result.get('segments', []))
                    features.extend(result.get('features', []))
                    embeddings.extend(result.get('embeddings', []))
            
            # Create final result
            result = self.create_success_result(
                segments=segments,
                features=features,
                embeddings=embeddings,
                metadata={
                    'video_info': await self._get_video_info(file_path),
                    'analysis_tasks': len(tasks),
                    'successful_tasks': len([r for r in results if not isinstance(r, Exception)])
                }
            )
            
            self.log_analysis_end(file_path, result)
            return result
            
        except Exception as e:
            logger.error(f"Video analysis failed", error=str(e))
            return self.create_error_result(str(e))
    
    async def _detect_scenes(self, file_path: str) -> Dict[str, Any]:
        """Detect scene changes in video"""
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return {'segments': [], 'features': [], 'embeddings': []}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            segments = []
            prev_frame = None
            scene_start = 0
            scene_count = 0
            
            # Simple scene detection based on frame differences
            threshold = 30.0  # Adjust based on video content
            
            for frame_idx in range(0, frame_count, int(fps)):  # Sample every second
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Convert to grayscale for comparison
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(prev_frame, gray)
                    mean_diff = np.mean(diff)
                    
                    if mean_diff > threshold:
                        # Scene change detected
                        scene_end = frame_idx / fps
                        
                        segments.append({
                            'type': 'scene',
                            'start_time': scene_start,
                            'end_time': scene_end,
                            'confidence': min(mean_diff / 100.0, 1.0),
                            'metadata': {
                                'scene_id': scene_count,
                                'frame_difference': mean_diff
                            }
                        })
                        
                        scene_start = scene_end
                        scene_count += 1
                
                prev_frame = gray
            
            # Add final scene
            if scene_start < duration:
                segments.append({
                    'type': 'scene',
                    'start_time': scene_start,
                    'end_time': duration,
                    'confidence': 0.8,
                    'metadata': {
                        'scene_id': scene_count,
                        'final_scene': True
                    }
                })
            
            cap.release()
            
            return {
                'segments': segments,
                'features': [{
                    'type': 'scene_count',
                    'domain': 'video',
                    'confidence': 1.0,
                    'data': {'count': len(segments)},
                    'metadata': {'analyzer': 'scene_detection'}
                }],
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Scene detection failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _extract_frames(self, file_path: str) -> Dict[str, Any]:
        """Extract key frames from video"""
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return {'segments': [], 'features': [], 'embeddings': []}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Extract frames at regular intervals
            frame_interval = max(1, int(fps * 5))  # Every 5 seconds
            key_frames = []
            
            for frame_idx in range(0, frame_count, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    timestamp = frame_idx / fps
                    
                    # Basic frame analysis
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    brightness = np.mean(gray)
                    contrast = np.std(gray)
                    
                    key_frames.append({
                        'timestamp': timestamp,
                        'brightness': brightness,
                        'contrast': contrast,
                        'frame_index': frame_idx
                    })
            
            cap.release()
            
            # Create segments for key frames
            segments = []
            for i, frame in enumerate(key_frames):
                segments.append({
                    'type': 'keyframe',
                    'start_time': frame['timestamp'],
                    'end_time': frame['timestamp'] + 0.1,  # Short duration
                    'confidence': 0.9,
                    'metadata': {
                        'frame_index': frame['frame_index'],
                        'brightness': frame['brightness'],
                        'contrast': frame['contrast']
                    }
                })
            
            return {
                'segments': segments,
                'features': [{
                    'type': 'keyframe_count',
                    'domain': 'video',
                    'confidence': 1.0,
                    'data': {'count': len(key_frames)},
                    'metadata': {'analyzer': 'frame_extraction'}
                }],
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Frame extraction failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """Analyze audio track of video"""
        try:
            # For now, return mock audio analysis
            # In production, use librosa or similar for audio analysis
            
            features = [{
                'type': 'audio_present',
                'domain': 'audio',
                'confidence': 0.8,
                'data': {'has_audio': True},
                'metadata': {'analyzer': 'audio_detection'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Audio analysis failed", error=str(e))
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _detect_objects(self, file_path: str) -> Dict[str, Any]:
        """Detect objects in video frames"""
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return {'segments': [], 'features': [], 'embeddings': []}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Sample frames for object detection
            sample_interval = max(1, int(fps * 10))  # Every 10 seconds
            detected_objects = set()
            
            for frame_idx in range(0, frame_count, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Simple object detection using OpenCV
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Detect faces (simple example)
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                    
                    if len(faces) > 0:
                        detected_objects.add('person')
                    
                    # Detect edges (simple feature)
                    edges = cv2.Canny(gray, 50, 150)
                    edge_density = np.sum(edges > 0) / edges.size
                    
                    if edge_density > 0.1:
                        detected_objects.add('high_detail')
            
            cap.release()
            
            # Create features for detected objects
            features = []
            for obj in detected_objects:
                features.append({
                    'type': f'object_{obj}',
                    'domain': 'visual',
                    'confidence': 0.7,
                    'data': {'object_type': obj},
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
    
    async def _get_video_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic video information"""
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return {}
            
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
            logger.error(f"Failed to get video info", error=str(e))
            return {}
