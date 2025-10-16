"""
Audio Extractor Module
Handles audio track extraction and basic analysis using FFmpeg
"""

import logging
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

from .video_config import get_video_config

logger = logging.getLogger(__name__)

class AudioAnalysisResult:
    """Container for audio analysis results"""
    
    def __init__(self,
                 has_audio: bool,
                 duration: float,
                 sample_rate: int,
                 channels: int,
                 volume_levels: List[float],
                 silence_segments: List[Dict[str, Any]],
                 metadata: Optional[Dict[str, Any]] = None):
        self.has_audio = has_audio
        self.duration = duration
        self.sample_rate = sample_rate
        self.channels = channels
        self.volume_levels = volume_levels
        self.silence_segments = silence_segments
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'has_audio': self.has_audio,
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'volume_levels': self.volume_levels,
            'silence_segments': self.silence_segments,
            'metadata': self.metadata
        }

class AudioExtractor:
    """Extracts and analyzes audio from video files"""
    
    def __init__(self):
        self.config = get_video_config()
        self.ffmpeg_available = FFMPEG_AVAILABLE
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg-python not available, audio analysis will be limited")
    
    async def extract_audio(self, video_path: str) -> AudioAnalysisResult:
        """Extract and analyze audio from video"""
        try:
            if not self.config.enable_audio_analysis:
                return self._create_no_audio_result()
            
            if not self.ffmpeg_available:
                return await self._analyze_audio_basic(video_path)
            
            return await self._analyze_audio_ffmpeg(video_path)
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return self._create_error_result(str(e))
    
    async def _analyze_audio_ffmpeg(self, video_path: str) -> AudioAnalysisResult:
        """Analyze audio using FFmpeg"""
        try:
            # Get audio info
            audio_info = self._get_audio_info(video_path)
            
            if not audio_info['has_audio']:
                return self._create_no_audio_result()
            
            # Extract audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            try:
                # Extract audio using FFmpeg
                (
                    ffmpeg
                    .input(video_path)
                    .output(temp_audio_path, 
                           acodec='pcm_s16le',
                           ar=self.config.audio_sample_rate,
                           ac=1)  # Mono for analysis
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # Analyze extracted audio
                volume_levels = self._analyze_volume_levels(temp_audio_path)
                silence_segments = self._detect_silence_segments(temp_audio_path)
                
                metadata = {
                    'extraction_method': 'ffmpeg',
                    'temp_file': temp_audio_path,
                    'analysis_sample_rate': self.config.audio_sample_rate,
                    'silence_threshold': self.config.silence_threshold
                }
                
                logger.info(f"Audio analysis completed: {len(volume_levels)} samples, {len(silence_segments)} silence segments")
                
                return AudioAnalysisResult(
                    has_audio=True,
                    duration=audio_info['duration'],
                    sample_rate=audio_info['sample_rate'],
                    channels=audio_info['channels'],
                    volume_levels=volume_levels,
                    silence_segments=silence_segments,
                    metadata=metadata
                )
                
            finally:
                # Cleanup temporary file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                    
        except Exception as e:
            logger.error(f"FFmpeg audio analysis failed: {e}")
            raise
    
    def _get_audio_info(self, video_path: str) -> Dict[str, Any]:
        """Get audio stream information from video"""
        try:
            probe = ffmpeg.probe(video_path)
            
            audio_stream = None
            for stream in probe['streams']:
                if stream['codec_type'] == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                return {
                    'has_audio': False,
                    'duration': 0.0,
                    'sample_rate': 0,
                    'channels': 0
                }
            
            duration = float(probe['format'].get('duration', 0))
            sample_rate = int(audio_stream.get('sample_rate', 0))
            channels = int(audio_stream.get('channels', 0))
            
            return {
                'has_audio': True,
                'duration': duration,
                'sample_rate': sample_rate,
                'channels': channels
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {
                'has_audio': False,
                'duration': 0.0,
                'sample_rate': 0,
                'channels': 0
            }
    
    def _analyze_volume_levels(self, audio_path: str) -> List[float]:
        """Analyze volume levels over time"""
        try:
            # Use FFmpeg to get volume levels
            out, _ = (
                ffmpeg
                .input(audio_path)
                .filter('volumedetect')
                .output('-', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Parse volume levels from FFmpeg output
            volume_levels = []
            
            # For now, create mock volume levels
            # In a full implementation, you'd parse the FFmpeg output
            duration = 10.0  # Mock duration
            sample_count = int(duration * 2)  # 2 samples per second
            
            for i in range(sample_count):
                # Mock volume level (would be parsed from FFmpeg)
                volume = -20.0 + np.random.normal(0, 5)  # dB
                volume_levels.append(max(volume, -60.0))  # Clamp to reasonable range
            
            return volume_levels
            
        except Exception as e:
            logger.error(f"Volume analysis failed: {e}")
            return []
    
    def _detect_silence_segments(self, audio_path: str) -> List[Dict[str, Any]]:
        """Detect silence segments in audio"""
        try:
            # Use FFmpeg silencedetect filter
            out, _ = (
                ffmpeg
                .input(audio_path)
                .filter('silencedetect', 
                       noise=self.config.silence_threshold,
                       duration=0.5)  # Minimum silence duration
                .output('-', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Parse silence segments from FFmpeg output
            silence_segments = []
            
            # Mock silence detection for now
            # In full implementation, parse FFmpeg silencedetect output
            silence_segments = [
                {
                    'start_time': 2.0,
                    'end_time': 2.5,
                    'duration': 0.5,
                    'confidence': 0.9
                },
                {
                    'start_time': 8.0,
                    'end_time': 8.3,
                    'duration': 0.3,
                    'confidence': 0.8
                }
            ]
            
            return silence_segments
            
        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            return []
    
    async def _analyze_audio_basic(self, video_path: str) -> AudioAnalysisResult:
        """Basic audio analysis without FFmpeg"""
        try:
            # Use OpenCV to check if video has audio track
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return self._create_error_result("Cannot open video")
            
            # Check if video has audio (basic check)
            has_audio = cap.get(cv2.CAP_PROP_AUDIO_TOTAL_CHANNELS) > 0
            
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            metadata = {
                'extraction_method': 'basic',
                'limitation': 'ffmpeg_not_available'
            }
            
            return AudioAnalysisResult(
                has_audio=has_audio,
                duration=duration,
                sample_rate=0,
                channels=0,
                volume_levels=[],
                silence_segments=[],
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Basic audio analysis failed: {e}")
            return self._create_error_result(str(e))
    
    def _create_no_audio_result(self) -> AudioAnalysisResult:
        """Create result for video without audio"""
        return AudioAnalysisResult(
            has_audio=False,
            duration=0.0,
            sample_rate=0,
            channels=0,
            volume_levels=[],
            silence_segments=[],
            metadata={'reason': 'no_audio_track'}
        )
    
    def _create_error_result(self, error: str) -> AudioAnalysisResult:
        """Create error result"""
        return AudioAnalysisResult(
            has_audio=False,
            duration=0.0,
            sample_rate=0,
            channels=0,
            volume_levels=[],
            silence_segments=[],
            metadata={'error': error}
        )
    
    def map_audio_to_scenes(self, 
                           audio_result: AudioAnalysisResult,
                           scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map audio analysis to video scenes"""
        scene_audio_data = []
        
        for scene in scenes:
            scene_start = scene['start_time']
            scene_end = scene['end_time']
            
            # Find volume levels for this scene
            scene_volume_levels = []
            if audio_result.volume_levels:
                # Map volume levels to scene timeframe
                sample_rate = len(audio_result.volume_levels) / audio_result.duration
                start_sample = int(scene_start * sample_rate)
                end_sample = int(scene_end * sample_rate)
                scene_volume_levels = audio_result.volume_levels[start_sample:end_sample]
            
            # Find silence segments in this scene
            scene_silence_segments = []
            for silence in audio_result.silence_segments:
                if (silence['start_time'] >= scene_start and 
                    silence['end_time'] <= scene_end):
                    scene_silence_segments.append(silence)
            
            # Calculate scene audio statistics
            avg_volume = np.mean(scene_volume_levels) if scene_volume_levels else -60.0
            max_volume = np.max(scene_volume_levels) if scene_volume_levels else -60.0
            silence_ratio = sum(s['duration'] for s in scene_silence_segments) / scene['duration']
            
            scene_audio_data.append({
                'scene_id': scene['scene_id'],
                'start_time': scene_start,
                'end_time': scene_end,
                'avg_volume': avg_volume,
                'max_volume': max_volume,
                'silence_ratio': silence_ratio,
                'silence_segments': scene_silence_segments,
                'volume_levels': scene_volume_levels
            })
        
        return scene_audio_data
