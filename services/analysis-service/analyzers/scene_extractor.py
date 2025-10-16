"""
Scene Extractor for Video Analysis
Extracts individual scenes as temporary low-resolution videos for analysis
"""

import cv2
import numpy as np
import logging
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .scene_detector_v2 import SceneSegment, EnhancedSceneDetector

logger = logging.getLogger(__name__)

@dataclass
class ExtractedScene:
    """Represents an extracted scene video"""
    scene_id: str
    video_path: str
    start_time: float
    end_time: float
    duration: float
    resolution: Tuple[int, int]
    fps: float
    frame_count: int
    file_size: int
    metadata: Dict[str, Any]

class SceneExtractor:
    """Extracts individual scenes as temporary video files"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'output_resolution': (640, 360),  # Low-res for faster processing
            'output_fps': 15,  # Reduced FPS
            'codec': 'mp4v',
            'quality': 50,  # Compression quality (0-100)
            'temp_dir': '/tmp/dataflux_scenes',
            'cleanup_after_analysis': True
        }
        
        # Create temp directory
        temp_dir = self.config.get('temp_dir', '/tmp/dataflux_scenes')
        os.makedirs(temp_dir, exist_ok=True)
        
        logger.info(f"🎬 Scene Extractor initialized with resolution: {self.config['output_resolution']}")
    
    def extract_scenes(self, video_path: str, scenes: List[SceneSegment]) -> List[ExtractedScene]:
        """
        Extract individual scenes as temporary video files
        
        Args:
            video_path: Path to original video
            scenes: List of detected scene segments
            
        Returns:
            List of ExtractedScene objects
        """
        try:
            logger.info(f"🎬 Extracting {len(scenes)} scenes from: {Path(video_path).name}")
            
            extracted_scenes = []
            
            for i, scene in enumerate(scenes):
                logger.info(f"📹 Extracting scene {i+1}/{len(scenes)}: {scene.scene_id}")
                
                extracted_scene = self._extract_single_scene(video_path, scene, i)
                if extracted_scene:
                    extracted_scenes.append(extracted_scene)
            
            logger.info(f"✅ Successfully extracted {len(extracted_scenes)} scenes")
            return extracted_scenes
            
        except Exception as e:
            logger.error(f"❌ Scene extraction failed: {e}")
            return []
    
    def _extract_single_scene(self, video_path: str, scene: SceneSegment, index: int) -> Optional[ExtractedScene]:
        """Extract a single scene as a video file"""
        try:
            # Open original video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video: {video_path}")
                return None
            
            # Get video properties
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate target resolution (maintain aspect ratio)
            target_width, target_height = self._calculate_target_resolution(
                original_width, original_height, self.config['output_resolution']
            )
            
            # Create output video path
            output_path = os.path.join(
                self.config['temp_dir'],
                f"{Path(video_path).stem}_scene_{scene.scene_id}.mp4"
            )
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*self.config['codec'])
            out = cv2.VideoWriter(
                output_path,
                fourcc,
                self.config['output_fps'],
                (target_width, target_height)
            )
            
            if not out.isOpened():
                logger.error(f"Cannot create output video: {output_path}")
                cap.release()
                return None
            
            # Seek to start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, scene.start_frame)
            
            frame_count = 0
            total_frames = scene.end_frame - scene.start_frame
            
            # Extract frames
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize frame to target resolution
                resized_frame = cv2.resize(frame, (target_width, target_height))
                
                # Write frame
                out.write(resized_frame)
                frame_count += 1
            
            # Cleanup
            cap.release()
            out.release()
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            # Create ExtractedScene object
            extracted_scene = ExtractedScene(
                scene_id=scene.scene_id,
                video_path=output_path,
                start_time=scene.start_time,
                end_time=scene.end_time,
                duration=scene.duration,
                resolution=(target_width, target_height),
                fps=self.config['output_fps'],
                frame_count=frame_count,
                file_size=file_size,
                metadata={
                    'original_resolution': (original_width, original_height),
                    'original_fps': original_fps,
                    'compression_ratio': file_size / (frame_count * target_width * target_height * 3),
                    'extraction_method': 'cv2_videowriter',
                    'scene_index': index
                }
            )
            
            logger.info(f"✅ Extracted scene {scene.scene_id}: {frame_count} frames, {file_size/1024:.1f}KB")
            return extracted_scene
            
        except Exception as e:
            logger.error(f"❌ Failed to extract scene {scene.scene_id}: {e}")
            return None
    
    def _calculate_target_resolution(self, original_width: int, original_height: int, 
                                   target_resolution: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate target resolution maintaining aspect ratio"""
        target_width, target_height = target_resolution
        
        # Calculate aspect ratio
        aspect_ratio = original_width / original_height
        
        # Adjust target resolution to maintain aspect ratio
        if aspect_ratio > target_width / target_height:
            # Video is wider than target
            target_height = int(target_width / aspect_ratio)
        else:
            # Video is taller than target
            target_width = int(target_height * aspect_ratio)
        
        # Ensure dimensions are even (required by some codecs)
        target_width = target_width - (target_width % 2)
        target_height = target_height - (target_height % 2)
        
        return target_width, target_height
    
    def cleanup_scene(self, extracted_scene: ExtractedScene) -> bool:
        """Clean up a single extracted scene file"""
        try:
            if os.path.exists(extracted_scene.video_path):
                os.remove(extracted_scene.video_path)
                logger.info(f"🗑️ Cleaned up scene: {extracted_scene.scene_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to cleanup scene {extracted_scene.scene_id}: {e}")
        return False
    
    def cleanup_all_scenes(self, extracted_scenes: List[ExtractedScene]) -> int:
        """Clean up all extracted scene files"""
        cleaned_count = 0
        for scene in extracted_scenes:
            if self.cleanup_scene(scene):
                cleaned_count += 1
        
        logger.info(f"🗑️ Cleaned up {cleaned_count}/{len(extracted_scenes)} scene files")
        return cleaned_count
    
    def get_scene_info(self, extracted_scene: ExtractedScene) -> Dict[str, Any]:
        """Get information about an extracted scene"""
        return {
            'scene_id': extracted_scene.scene_id,
            'duration': extracted_scene.duration,
            'resolution': extracted_scene.resolution,
            'fps': extracted_scene.fps,
            'frame_count': extracted_scene.frame_count,
            'file_size_mb': extracted_scene.file_size / (1024 * 1024),
            'compression_ratio': extracted_scene.metadata.get('compression_ratio', 0),
            'file_path': extracted_scene.video_path
        }

# Factory function
def create_scene_extractor(config: Dict[str, Any] = None) -> SceneExtractor:
    """Create a scene extractor instance"""
    return SceneExtractor(config)
