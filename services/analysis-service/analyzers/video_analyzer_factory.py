"""
Video Analyzer Factory
Creates the appropriate video analyzer based on availability
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def create_video_analyzer(config: Dict[str, Any] = None) -> Any:
    """
    Create the best available video analyzer
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Video analyzer instance
    """
    
    # Try to create V2 analyzer (scene-based pipeline)
    try:
        from .video_analyzer_v2 import EnhancedVideoAnalyzerV2, create_enhanced_video_analyzer_v2
        
        v2_config = config or {
            'scene_detection': {
                'method': 'histogram_diff',
                'threshold': 0.3,
                'min_scene_duration': 1.0,
                'max_scenes': 20
            },
            'scene_extraction': {
                'output_resolution': (640, 360),
                'output_fps': 15,
                'quality': 50
            },
            'scene_analysis': {
                'frame_sampling_rate': 0.5,
                'max_frames_per_scene': 8,
                'enable_object_detection': True,
                'enable_scene_classification': True,
                'enable_color_analysis': True,
                'enable_motion_analysis': True,
                'enable_quality_assessment': True
            },
            'cleanup_temp_files': True,
            'max_concurrent_scenes': 3
        }
        
        analyzer = create_enhanced_video_analyzer_v2(v2_config)
        logger.info("🎬 Using Enhanced Video Analyzer V2 (Scene-based pipeline)")
        return analyzer
        
    except ImportError as e:
        logger.warning(f"⚠️ Enhanced Video Analyzer V2 not available: {e}")
    
    # Fallback to V1 analyzer
    try:
        from .video_analyzer import EnhancedVideoAnalyzer
        
        analyzer = EnhancedVideoAnalyzer()
        logger.info("🎬 Using Enhanced Video Analyzer V1 (Legacy pipeline)")
        return analyzer
        
    except ImportError as e:
        logger.error(f"❌ No video analyzer available: {e}")
        raise RuntimeError("No video analyzer available")

# Create the analyzer instance
enhanced_video_analyzer = create_video_analyzer()
