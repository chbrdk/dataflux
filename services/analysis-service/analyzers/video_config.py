"""
Video Analysis Configuration Manager
Centralized configuration for video analysis pipeline
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ClaudeVisionMode(Enum):
    """Claude Vision analysis modes"""
    ALL_FRAMES = "all_frames"
    KEYFRAMES_ONLY = "keyframes_only"
    DISABLED = "disabled"

class SceneDetectionMethod(Enum):
    """Scene detection methods"""
    CONTENT_DETECTOR = "content_detector"
    ADAPTIVE_DETECTOR = "adaptive_detector"
    THRESHOLD_DETECTOR = "threshold_detector"
    COMBINED = "combined"

@dataclass
class VideoAnalysisConfig:
    """Configuration for video analysis pipeline"""
    
    # Frame sampling settings
    frame_sampling_rate: float = 2.5  # Seconds between frames
    adaptive_sampling: bool = True  # More frames for high-activity scenes
    max_frames_per_scene: int = 20  # Limit frames per scene
    
    # Scene detection settings
    scene_detection_method: SceneDetectionMethod = SceneDetectionMethod.COMBINED
    content_threshold: float = 27.0  # ContentDetector threshold
    adaptive_threshold: float = 12.0  # AdaptiveDetector threshold
    min_scene_length: float = 1.0  # Minimum scene length in seconds
    
    # Claude Vision settings
    claude_vision_mode: ClaudeVisionMode = ClaudeVisionMode.KEYFRAMES_ONLY
    claude_vision_rate_limit: int = 10  # Max requests per minute
    
    # Parallel processing settings
    max_parallel_frames: int = 5  # Max concurrent frame analyses
    batch_size: int = 3  # Frames per batch
    
    # Audio analysis settings
    enable_audio_analysis: bool = True
    audio_sample_rate: int = 16000  # Hz
    silence_threshold: float = -40.0  # dB
    
    # Temporal analysis settings
    enable_movement_tracking: bool = True
    enable_object_tracking: bool = True
    movement_threshold: float = 0.1  # Minimum movement to track
    
    # Output settings
    generate_thumbnails: bool = True
    thumbnail_size: tuple = (320, 240)  # Width, Height
    save_intermediate_frames: bool = False  # For debugging
    
    # Performance settings
    enable_gpu_acceleration: bool = True
    memory_limit_mb: int = 2048  # Max memory usage
    timeout_seconds: int = 300  # Analysis timeout
    
    @classmethod
    def from_environment(cls) -> 'VideoAnalysisConfig':
        """Create config from environment variables"""
        return cls(
            frame_sampling_rate=float(os.getenv('VIDEO_FRAME_SAMPLING_RATE', '2.5')),
            adaptive_sampling=os.getenv('VIDEO_ADAPTIVE_SAMPLING', 'true').lower() == 'true',
            max_frames_per_scene=int(os.getenv('VIDEO_MAX_FRAMES_PER_SCENE', '20')),
            
            scene_detection_method=SceneDetectionMethod(
                os.getenv('VIDEO_SCENE_DETECTION_METHOD', 'combined')
            ),
            content_threshold=float(os.getenv('VIDEO_CONTENT_THRESHOLD', '27.0')),
            adaptive_threshold=float(os.getenv('VIDEO_ADAPTIVE_THRESHOLD', '12.0')),
            min_scene_length=float(os.getenv('VIDEO_MIN_SCENE_LENGTH', '1.0')),
            
            claude_vision_mode=ClaudeVisionMode(
                os.getenv('CLAUDE_VISION_MODE', 'keyframes_only')
            ),
            claude_vision_rate_limit=int(os.getenv('CLAUDE_VISION_RATE_LIMIT', '10')),
            
            max_parallel_frames=int(os.getenv('VIDEO_MAX_PARALLEL_FRAMES', '5')),
            batch_size=int(os.getenv('VIDEO_BATCH_SIZE', '3')),
            
            enable_audio_analysis=os.getenv('VIDEO_ENABLE_AUDIO', 'true').lower() == 'true',
            audio_sample_rate=int(os.getenv('VIDEO_AUDIO_SAMPLE_RATE', '16000')),
            silence_threshold=float(os.getenv('VIDEO_SILENCE_THRESHOLD', '-40.0')),
            
            enable_movement_tracking=os.getenv('VIDEO_ENABLE_MOVEMENT', 'true').lower() == 'true',
            enable_object_tracking=os.getenv('VIDEO_ENABLE_OBJECT_TRACKING', 'true').lower() == 'true',
            movement_threshold=float(os.getenv('VIDEO_MOVEMENT_THRESHOLD', '0.1')),
            
            generate_thumbnails=os.getenv('VIDEO_GENERATE_THUMBNAILS', 'true').lower() == 'true',
            save_intermediate_frames=os.getenv('VIDEO_SAVE_INTERMEDIATE', 'false').lower() == 'true',
            
            enable_gpu_acceleration=os.getenv('VIDEO_ENABLE_GPU', 'true').lower() == 'true',
            memory_limit_mb=int(os.getenv('VIDEO_MEMORY_LIMIT_MB', '2048')),
            timeout_seconds=int(os.getenv('VIDEO_TIMEOUT_SECONDS', '300'))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'frame_sampling_rate': self.frame_sampling_rate,
            'adaptive_sampling': self.adaptive_sampling,
            'max_frames_per_scene': self.max_frames_per_scene,
            'scene_detection_method': self.scene_detection_method.value,
            'content_threshold': self.content_threshold,
            'adaptive_threshold': self.adaptive_threshold,
            'min_scene_length': self.min_scene_length,
            'claude_vision_mode': self.claude_vision_mode.value,
            'claude_vision_rate_limit': self.claude_vision_rate_limit,
            'max_parallel_frames': self.max_parallel_frames,
            'batch_size': self.batch_size,
            'enable_audio_analysis': self.enable_audio_analysis,
            'audio_sample_rate': self.audio_sample_rate,
            'silence_threshold': self.silence_threshold,
            'enable_movement_tracking': self.enable_movement_tracking,
            'enable_object_tracking': self.enable_object_tracking,
            'movement_threshold': self.movement_threshold,
            'generate_thumbnails': self.generate_thumbnails,
            'thumbnail_size': self.thumbnail_size,
            'save_intermediate_frames': self.save_intermediate_frames,
            'enable_gpu_acceleration': self.enable_gpu_acceleration,
            'memory_limit_mb': self.memory_limit_mb,
            'timeout_seconds': self.timeout_seconds
        }
    
    def validate(self) -> bool:
        """Validate configuration values"""
        if self.frame_sampling_rate <= 0:
            raise ValueError("frame_sampling_rate must be positive")
        if self.max_frames_per_scene <= 0:
            raise ValueError("max_frames_per_scene must be positive")
        if self.content_threshold <= 0:
            raise ValueError("content_threshold must be positive")
        if self.max_parallel_frames <= 0:
            raise ValueError("max_parallel_frames must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        return True

# Global config instance
_config: Optional[VideoAnalysisConfig] = None

def get_video_config() -> VideoAnalysisConfig:
    """Get global video analysis configuration"""
    global _config
    if _config is None:
        _config = VideoAnalysisConfig.from_environment()
        _config.validate()
    return _config

def set_video_config(config: VideoAnalysisConfig) -> None:
    """Set global video analysis configuration"""
    global _config
    config.validate()
    _config = config
