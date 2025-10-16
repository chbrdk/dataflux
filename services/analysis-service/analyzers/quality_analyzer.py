#!/usr/bin/env python3
"""
Quality Assessment für Video/Frame quality und Camera motion
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class QualityMetrics:
    """Video Quality Metrics"""
    resolution: Tuple[int, int]
    bitrate: Optional[float] = None
    fps: float = 0.0
    compression_ratio: Optional[float] = None
    overall_quality_score: float = 0.0

@dataclass
class FrameQualityMetrics:
    """Frame Quality Metrics"""
    blur_score: float
    noise_score: float
    brightness_score: float
    contrast_score: float
    sharpness_score: float
    overall_score: float

@dataclass
class CameraMotionMetrics:
    """Camera Motion Metrics"""
    pan_speed: float  # degrees per second
    tilt_speed: float  # degrees per second
    zoom_speed: float  # zoom factor per second
    shake_intensity: float  # shake magnitude
    motion_type: str  # static, pan, tilt, zoom, shake, complex
    stability_score: float  # 0-1, higher is more stable

@dataclass
class LightingMetrics:
    """Lighting Analysis Metrics"""
    brightness_level: str  # dark, normal, bright, overexposed
    contrast_level: str  # low, normal, high
    color_temperature: Optional[float] = None  # Kelvin
    lighting_quality_score: float = 0.0

@dataclass
class QualityAssessmentResult:
    """Complete Quality Assessment Result"""
    video_quality: QualityMetrics
    frame_quality: List[FrameQualityMetrics]
    camera_motion: CameraMotionMetrics
    lighting: LightingMetrics
    overall_quality_score: float
    recommendations: List[str]

class QualityAnalyzer:
    """Video and Frame Quality Analysis"""
    
    def __init__(self):
        logger.info("QualityAnalyzer initialized")
    
    async def analyze_video_quality(self, video_path: str) -> QualityAssessmentResult:
        """
        Comprehensive quality analysis of a video
        
        Args:
            video_path: Path to video file
        
        Returns:
            QualityAssessmentResult with all quality metrics
        """
        logger.info(f"Starting quality analysis for {video_path}")
        
        try:
            # Get video metadata
            video_quality = await self._analyze_video_metadata(video_path)
            
            # Analyze frame quality
            frame_quality = await self._analyze_frame_quality(video_path)
            
            # Analyze camera motion
            camera_motion = await self._analyze_camera_motion(video_path)
            
            # Analyze lighting
            lighting = await self._analyze_lighting(video_path)
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_quality_score(
                video_quality, frame_quality, camera_motion, lighting
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                video_quality, frame_quality, camera_motion, lighting
            )
            
            result = QualityAssessmentResult(
                video_quality=video_quality,
                frame_quality=frame_quality,
                camera_motion=camera_motion,
                lighting=lighting,
                overall_quality_score=overall_score,
                recommendations=recommendations
            )
            
            logger.info(f"Quality analysis completed: {overall_score:.2f} overall score")
            return result
            
        except Exception as e:
            logger.error(f"Error in quality analysis: {e}")
            raise
    
    async def _analyze_video_metadata(self, video_path: str) -> QualityMetrics:
        """Analyze video metadata and basic quality metrics"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            # Get basic properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate duration
            duration = frame_count / fps if fps > 0 else 0
            
            # Estimate bitrate (if file size is available)
            file_size = Path(video_path).stat().st_size
            bitrate = (file_size * 8) / duration if duration > 0 else None
            
            # Calculate compression ratio (rough estimate)
            uncompressed_size = width * height * 3 * frame_count  # RGB bytes
            compression_ratio = file_size / uncompressed_size if uncompressed_size > 0 else None
            
            # Calculate quality score based on resolution and bitrate
            quality_score = self._calculate_video_quality_score(
                width, height, fps, bitrate, compression_ratio
            )
            
            cap.release()
            
            return QualityMetrics(
                resolution=(width, height),
                bitrate=bitrate,
                fps=fps,
                compression_ratio=compression_ratio,
                overall_quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing video metadata: {e}")
            return QualityMetrics(resolution=(0, 0), overall_quality_score=0.0)
    
    def _calculate_video_quality_score(self, 
                                     width: int, 
                                     height: int, 
                                     fps: float, 
                                     bitrate: Optional[float],
                                     compression_ratio: Optional[float]) -> float:
        """Calculate video quality score"""
        score = 0.0
        
        # Resolution score (0-0.4)
        resolution_score = min(1.0, (width * height) / (1920 * 1080))  # Normalize to 1080p
        score += resolution_score * 0.4
        
        # FPS score (0-0.2)
        fps_score = min(1.0, fps / 30.0)  # Normalize to 30fps
        score += fps_score * 0.2
        
        # Bitrate score (0-0.2)
        if bitrate:
            # Assume good bitrate is 5-10 Mbps for 1080p
            bitrate_score = min(1.0, bitrate / (8 * 1024 * 1024))  # Convert to Mbps
            score += bitrate_score * 0.2
        
        # Compression score (0-0.2)
        if compression_ratio:
            # Lower compression ratio is better (less compressed)
            compression_score = max(0.0, 1.0 - compression_ratio)
            score += compression_score * 0.2
        
        return min(1.0, score)
    
    async def _analyze_frame_quality(self, video_path: str) -> List[FrameQualityMetrics]:
        """Analyze quality of individual frames"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Sample frames for analysis (every 30 frames or 1 second)
            sample_interval = max(1, int(fps)) if fps > 0 else 30
            frame_qualities = []
            
            frame_idx = 0
            while frame_idx < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Analyze frame quality
                quality_metrics = self._analyze_single_frame(frame)
                frame_qualities.append(quality_metrics)
                
                frame_idx += sample_interval
            
            cap.release()
            
            logger.info(f"Analyzed {len(frame_qualities)} frames for quality")
            return frame_qualities
            
        except Exception as e:
            logger.error(f"Error analyzing frame quality: {e}")
            return []
    
    def _analyze_single_frame(self, frame: np.ndarray) -> FrameQualityMetrics:
        """Analyze quality of a single frame"""
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Blur detection using Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Noise detection using standard deviation
        noise_score = np.std(gray)
        
        # Brightness analysis
        brightness_score = np.mean(gray) / 255.0
        
        # Contrast analysis
        contrast_score = np.std(gray) / 255.0
        
        # Sharpness analysis (edge detection)
        edges = cv2.Canny(gray, 50, 150)
        sharpness_score = np.sum(edges) / (frame.shape[0] * frame.shape[1])
        
        # Overall frame quality score
        overall_score = self._calculate_frame_quality_score(
            blur_score, noise_score, brightness_score, contrast_score, sharpness_score
        )
        
        return FrameQualityMetrics(
            blur_score=blur_score,
            noise_score=noise_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            sharpness_score=sharpness_score,
            overall_score=overall_score
        )
    
    def _calculate_frame_quality_score(self, 
                                     blur_score: float,
                                     noise_score: float,
                                     brightness_score: float,
                                     contrast_score: float,
                                     sharpness_score: float) -> float:
        """Calculate overall frame quality score"""
        # Normalize scores (these are rough thresholds)
        blur_norm = min(1.0, blur_score / 1000.0)  # Higher is better
        noise_norm = max(0.0, 1.0 - (noise_score / 50.0))  # Lower is better
        brightness_norm = 1.0 - abs(brightness_score - 0.5) * 2  # 0.5 is ideal
        contrast_norm = min(1.0, contrast_score * 4)  # Higher is better
        sharpness_norm = min(1.0, sharpness_score * 10)  # Higher is better
        
        # Weighted average
        overall_score = (
            blur_norm * 0.3 +
            noise_norm * 0.2 +
            brightness_norm * 0.2 +
            contrast_norm * 0.15 +
            sharpness_norm * 0.15
        )
        
        return min(1.0, max(0.0, overall_score))
    
    async def _analyze_camera_motion(self, video_path: str) -> CameraMotionMetrics:
        """Analyze camera motion patterns"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Sample frames for motion analysis
            sample_interval = max(1, int(fps / 2)) if fps > 0 else 15  # Every 0.5 seconds
            prev_frame = None
            motion_vectors = []
            
            frame_idx = 0
            while frame_idx < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                if prev_frame is not None:
                    # Calculate optical flow
                    motion_vector = self._calculate_optical_flow(prev_frame, frame)
                    if motion_vector is not None:
                        motion_vectors.append(motion_vector)
                
                prev_frame = frame.copy()
                frame_idx += sample_interval
            
            cap.release()
            
            # Analyze motion patterns
            return self._analyze_motion_patterns(motion_vectors, fps)
            
        except Exception as e:
            logger.error(f"Error analyzing camera motion: {e}")
            return CameraMotionMetrics(
                pan_speed=0.0,
                tilt_speed=0.0,
                zoom_speed=0.0,
                shake_intensity=0.0,
                motion_type="unknown",
                stability_score=0.0
            )
    
    def _calculate_optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Optional[np.ndarray]:
        """Calculate optical flow between two frames"""
        try:
            # Convert to grayscale
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate optical flow
            flow = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray,
                np.array([[prev_gray.shape[1]//2, prev_gray.shape[0]//2]], dtype=np.float32),
                None
            )[0]
            
            if flow is not None and len(flow) > 0:
                return flow[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Error calculating optical flow: {e}")
            return None
    
    def _analyze_motion_patterns(self, motion_vectors: List[np.ndarray], fps: float) -> CameraMotionMetrics:
        """Analyze motion patterns from optical flow vectors"""
        if not motion_vectors:
            return CameraMotionMetrics(
                pan_speed=0.0,
                tilt_speed=0.0,
                zoom_speed=0.0,
                shake_intensity=0.0,
                motion_type="static",
                stability_score=1.0
            )
        
        # Convert to numpy array
        vectors = np.array(motion_vectors)
        
        # Calculate motion statistics
        pan_speed = np.mean(np.abs(vectors[:, 0])) * fps  # pixels per second
        tilt_speed = np.mean(np.abs(vectors[:, 1])) * fps  # pixels per second
        
        # Estimate zoom (simplified)
        zoom_speed = 0.0  # Would need more sophisticated analysis
        
        # Calculate shake intensity
        shake_intensity = np.std(vectors)
        
        # Determine motion type
        motion_type = self._classify_motion_type(vectors, pan_speed, tilt_speed, shake_intensity)
        
        # Calculate stability score
        stability_score = self._calculate_stability_score(pan_speed, tilt_speed, shake_intensity)
        
        return CameraMotionMetrics(
            pan_speed=pan_speed,
            tilt_speed=tilt_speed,
            zoom_speed=zoom_speed,
            shake_intensity=shake_intensity,
            motion_type=motion_type,
            stability_score=stability_score
        )
    
    def _classify_motion_type(self, 
                           vectors: np.ndarray, 
                           pan_speed: float, 
                           tilt_speed: float, 
                           shake_intensity: float) -> str:
        """Classify camera motion type"""
        if shake_intensity > 5.0:
            return "shake"
        elif pan_speed > 10.0 and tilt_speed < 5.0:
            return "pan"
        elif tilt_speed > 10.0 and pan_speed < 5.0:
            return "tilt"
        elif pan_speed > 5.0 and tilt_speed > 5.0:
            return "complex"
        elif pan_speed < 2.0 and tilt_speed < 2.0:
            return "static"
        else:
            return "mixed"
    
    def _calculate_stability_score(self, pan_speed: float, tilt_speed: float, shake_intensity: float) -> float:
        """Calculate camera stability score"""
        # Lower motion = higher stability
        pan_stability = max(0.0, 1.0 - (pan_speed / 20.0))
        tilt_stability = max(0.0, 1.0 - (tilt_speed / 20.0))
        shake_stability = max(0.0, 1.0 - (shake_intensity / 10.0))
        
        return (pan_stability + tilt_stability + shake_stability) / 3.0
    
    async def _analyze_lighting(self, video_path: str) -> LightingMetrics:
        """Analyze lighting conditions"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            # Sample frames for lighting analysis
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            sample_frames = min(10, frame_count // 10)  # Sample 10 frames
            
            brightness_values = []
            contrast_values = []
            
            for i in range(sample_frames):
                frame_idx = i * (frame_count // sample_frames)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    brightness, contrast = self._analyze_frame_lighting(frame)
                    brightness_values.append(brightness)
                    contrast_values.append(contrast)
            
            cap.release()
            
            # Calculate average lighting metrics
            avg_brightness = np.mean(brightness_values) if brightness_values else 0.5
            avg_contrast = np.mean(contrast_values) if contrast_values else 0.5
            
            # Classify lighting levels
            brightness_level = self._classify_brightness(avg_brightness)
            contrast_level = self._classify_contrast(avg_contrast)
            
            # Calculate lighting quality score
            lighting_quality_score = self._calculate_lighting_quality_score(avg_brightness, avg_contrast)
            
            return LightingMetrics(
                brightness_level=brightness_level,
                contrast_level=contrast_level,
                lighting_quality_score=lighting_quality_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing lighting: {e}")
            return LightingMetrics(
                brightness_level="unknown",
                contrast_level="unknown",
                lighting_quality_score=0.0
            )
    
    def _analyze_frame_lighting(self, frame: np.ndarray) -> Tuple[float, float]:
        """Analyze lighting in a single frame"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate brightness (mean intensity)
        brightness = np.mean(gray) / 255.0
        
        # Calculate contrast (standard deviation)
        contrast = np.std(gray) / 255.0
        
        return brightness, contrast
    
    def _classify_brightness(self, brightness: float) -> str:
        """Classify brightness level"""
        if brightness < 0.2:
            return "dark"
        elif brightness < 0.4:
            return "dim"
        elif brightness < 0.7:
            return "normal"
        elif brightness < 0.9:
            return "bright"
        else:
            return "overexposed"
    
    def _classify_contrast(self, contrast: float) -> str:
        """Classify contrast level"""
        if contrast < 0.2:
            return "low"
        elif contrast < 0.5:
            return "normal"
        else:
            return "high"
    
    def _calculate_lighting_quality_score(self, brightness: float, contrast: float) -> float:
        """Calculate lighting quality score"""
        # Ideal brightness is around 0.5
        brightness_score = 1.0 - abs(brightness - 0.5) * 2
        
        # Higher contrast is generally better
        contrast_score = min(1.0, contrast * 2)
        
        return (brightness_score + contrast_score) / 2.0
    
    def _calculate_overall_quality_score(self, 
                                       video_quality: QualityMetrics,
                                       frame_quality: List[FrameQualityMetrics],
                                       camera_motion: CameraMotionMetrics,
                                       lighting: LightingMetrics) -> float:
        """Calculate overall quality score"""
        # Video quality weight: 0.3
        video_score = video_quality.overall_quality_score * 0.3
        
        # Frame quality weight: 0.3
        frame_scores = [fq.overall_score for fq in frame_quality]
        avg_frame_score = np.mean(frame_scores) if frame_scores else 0.0
        frame_score = avg_frame_score * 0.3
        
        # Camera motion weight: 0.2
        motion_score = camera_motion.stability_score * 0.2
        
        # Lighting weight: 0.2
        lighting_score = lighting.lighting_quality_score * 0.2
        
        return video_score + frame_score + motion_score + lighting_score
    
    def _generate_recommendations(self, 
                                video_quality: QualityMetrics,
                                frame_quality: List[FrameQualityMetrics],
                                camera_motion: CameraMotionMetrics,
                                lighting: LightingMetrics) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        # Video quality recommendations
        if video_quality.overall_quality_score < 0.5:
            recommendations.append("Consider using higher resolution or bitrate for better video quality")
        
        if video_quality.fps < 24:
            recommendations.append("Low frame rate detected - consider recording at 24fps or higher")
        
        # Frame quality recommendations
        frame_scores = [fq.overall_score for fq in frame_quality]
        avg_frame_score = np.mean(frame_scores) if frame_scores else 0.0
        
        if avg_frame_score < 0.5:
            recommendations.append("Frame quality is low - check focus, lighting, and camera stability")
        
        # Camera motion recommendations
        if camera_motion.stability_score < 0.5:
            recommendations.append("Camera motion is unstable - use tripod or stabilization")
        
        if camera_motion.motion_type == "shake":
            recommendations.append("Excessive camera shake detected - use image stabilization")
        
        # Lighting recommendations
        if lighting.brightness_level in ["dark", "overexposed"]:
            recommendations.append(f"Lighting is {lighting.brightness_level} - adjust exposure settings")
        
        if lighting.contrast_level == "low":
            recommendations.append("Low contrast detected - improve lighting setup")
        
        return recommendations
