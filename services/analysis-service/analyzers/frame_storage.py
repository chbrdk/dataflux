"""
Frame Storage Manager
Handles temporary frame extraction, storage, and cleanup for video analysis
"""

import os
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import uuid

from .video_config import get_video_config

logger = logging.getLogger(__name__)

class FrameData:
    """Container for frame data and metadata"""
    
    def __init__(self, 
                 frame_id: str,
                 timestamp: float,
                 scene_id: int,
                 frame_index: int,
                 image_path: str,
                 thumbnail_path: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.frame_id = frame_id
        self.timestamp = timestamp
        self.scene_id = scene_id
        self.frame_index = frame_index
        self.image_path = image_path
        self.thumbnail_path = thumbnail_path
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'frame_id': self.frame_id,
            'timestamp': self.timestamp,
            'scene_id': self.scene_id,
            'frame_index': self.frame_index,
            'image_path': self.image_path,
            'thumbnail_path': self.thumbnail_path,
            'metadata': self.metadata
        }

class FrameStorageManager:
    """Manages temporary frame storage and cleanup"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.config = get_video_config()
        self.base_dir = base_dir or tempfile.mkdtemp(prefix='dataflux_video_')
        self.frames_dir = Path(self.base_dir) / 'frames'
        self.thumbnails_dir = Path(self.base_dir) / 'thumbnails'
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        self._extracted_frames: List[FrameData] = []
        self._cleanup_registered = False
        
        logger.info(f"FrameStorageManager initialized with base_dir: {self.base_dir}")
    
    def extract_frames_from_video(self, 
                                 video_path: str, 
                                 timestamps: List[float],
                                 scene_id: int = 0) -> List[FrameData]:
        """Extract frames at specified timestamps from video"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            extracted_frames = []
            
            for i, timestamp in enumerate(timestamps):
                frame_index = int(timestamp * fps)
                
                # Ensure frame index is within bounds
                if frame_index >= frame_count:
                    frame_index = frame_count - 1
                
                # Seek to frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame at timestamp {timestamp}")
                    continue
                
                # Generate unique frame ID
                frame_id = str(uuid.uuid4())
                
                # Save frame as image
                frame_filename = f"frame_{frame_id}.jpg"
                frame_path = self.frames_dir / frame_filename
                
                # Convert BGR to RGB and save
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                pil_image.save(frame_path, quality=95)
                
                # Generate thumbnail if enabled
                thumbnail_path = None
                if self.config.generate_thumbnails:
                    thumbnail_path = self._generate_thumbnail(
                        frame_rgb, frame_id, self.config.thumbnail_size
                    )
                
                # Create FrameData
                frame_data = FrameData(
                    frame_id=frame_id,
                    timestamp=timestamp,
                    scene_id=scene_id,
                    frame_index=frame_index,
                    image_path=str(frame_path),
                    thumbnail_path=thumbnail_path,
                    metadata={
                        'fps': fps,
                        'frame_count': frame_count,
                        'video_width': frame.shape[1],
                        'video_height': frame.shape[0],
                        'extraction_method': 'opencv'
                    }
                )
                
                extracted_frames.append(frame_data)
                self._extracted_frames.append(frame_data)
                
                logger.debug(f"Extracted frame at {timestamp}s -> {frame_path}")
            
            cap.release()
            logger.info(f"Extracted {len(extracted_frames)} frames from video")
            return extracted_frames
            
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            raise
    
    def extract_frames_from_scenes(self, 
                                 video_path: str, 
                                 scenes: List[Dict[str, Any]]) -> List[FrameData]:
        """Extract frames from video scenes with intelligent sampling"""
        all_frames = []
        
        for scene_idx, scene in enumerate(scenes):
            start_time = scene.get('start_time', 0)
            end_time = scene.get('end_time', start_time + 1)
            duration = end_time - start_time
            
            # Calculate frame timestamps for this scene
            timestamps = self._calculate_scene_timestamps(
                start_time, end_time, duration, scene_idx
            )
            
            # Extract frames for this scene
            scene_frames = self.extract_frames_from_video(
                video_path, timestamps, scene_idx
            )
            
            all_frames.extend(scene_frames)
        
        return all_frames
    
    def _calculate_scene_timestamps(self, 
                                  start_time: float, 
                                  end_time: float, 
                                  duration: float,
                                  scene_idx: int) -> List[float]:
        """Calculate optimal timestamps for frame extraction in a scene"""
        timestamps = []
        
        # Always include scene boundaries
        timestamps.append(start_time)
        if duration > 0.1:  # Avoid duplicate if very short scene
            timestamps.append(end_time)
        
        # Regular sampling within scene
        if duration > self.config.frame_sampling_rate:
            current_time = start_time + self.config.frame_sampling_rate
            while current_time < end_time - 0.1:  # Leave small buffer
                timestamps.append(current_time)
                current_time += self.config.frame_sampling_rate
        
        # Adaptive sampling for longer scenes
        if self.config.adaptive_sampling and duration > 10.0:
            # Add more frames for longer scenes
            additional_frames = min(
                int(duration / 5.0),  # One frame every 5 seconds
                self.config.max_frames_per_scene - len(timestamps)
            )
            
            for i in range(1, additional_frames + 1):
                adaptive_time = start_time + (duration * i / (additional_frames + 1))
                if adaptive_time not in timestamps:
                    timestamps.append(adaptive_time)
        
        # Sort and remove duplicates
        timestamps = sorted(list(set(timestamps)))
        
        # Limit to max_frames_per_scene
        if len(timestamps) > self.config.max_frames_per_scene:
            # Keep boundaries and sample evenly
            step = len(timestamps) / self.config.max_frames_per_scene
            timestamps = [timestamps[int(i * step)] for i in range(self.config.max_frames_per_scene)]
        
        logger.debug(f"Scene {scene_idx}: {len(timestamps)} timestamps calculated")
        return timestamps
    
    def _generate_thumbnail(self, 
                           frame_rgb: np.ndarray, 
                           frame_id: str, 
                           size: Tuple[int, int]) -> str:
        """Generate thumbnail for frame"""
        try:
            thumbnail_filename = f"thumb_{frame_id}.jpg"
            thumbnail_path = self.thumbnails_dir / thumbnail_filename
            
            # Resize frame
            pil_image = Image.fromarray(frame_rgb)
            pil_image.thumbnail(size, Image.Resampling.LANCZOS)
            pil_image.save(thumbnail_path, quality=85)
            
            return str(thumbnail_path)
            
        except Exception as e:
            logger.warning(f"Thumbnail generation failed for frame {frame_id}: {e}")
            return None
    
    def get_frame_data(self, frame_id: str) -> Optional[FrameData]:
        """Get frame data by ID"""
        for frame in self._extracted_frames:
            if frame.frame_id == frame_id:
                return frame
        return None
    
    def get_frames_by_scene(self, scene_id: int) -> List[FrameData]:
        """Get all frames for a specific scene"""
        return [frame for frame in self._extracted_frames if frame.scene_id == scene_id]
    
    def get_all_frames(self) -> List[FrameData]:
        """Get all extracted frames"""
        return self._extracted_frames.copy()
    
    def cleanup(self) -> None:
        """Clean up temporary files and directories"""
        try:
            if os.path.exists(self.base_dir):
                shutil.rmtree(self.base_dir)
                logger.info(f"Cleaned up frame storage: {self.base_dir}")
            
            self._extracted_frames.clear()
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
    
    def __del__(self):
        """Destructor with cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during destruction

class FrameCache:
    """Simple frame cache for repeated access"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: Dict[str, np.ndarray] = {}
        self._access_order: List[str] = []
    
    def get(self, frame_path: str) -> Optional[np.ndarray]:
        """Get frame from cache"""
        if frame_path in self._cache:
            # Move to end of access order
            self._access_order.remove(frame_path)
            self._access_order.append(frame_path)
            return self._cache[frame_path]
        return None
    
    def put(self, frame_path: str, frame: np.ndarray) -> None:
        """Put frame in cache"""
        if len(self._cache) >= self.max_size:
            # Remove least recently used
            lru_path = self._access_order.pop(0)
            del self._cache[lru_path]
        
        self._cache[frame_path] = frame
        self._access_order.append(frame_path)
    
    def clear(self) -> None:
        """Clear cache"""
        self._cache.clear()
        self._access_order.clear()
