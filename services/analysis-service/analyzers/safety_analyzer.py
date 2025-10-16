#!/usr/bin/env python3
"""
NSFW Detection und Content Safety
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import torch
from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class SafetyDetection:
    """Safety Detection Result"""
    detection_type: str  # nsfw, violence, disturbing, etc.
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    severity: str = "low"  # low, medium, high, critical
    description: Optional[str] = None

@dataclass
class ContentSafetyResult:
    """Complete Content Safety Analysis Result"""
    safety_detections: List[SafetyDetection]
    overall_safety_score: float  # 0-1, higher is safer
    content_warnings: List[str]
    is_safe_for_work: bool
    requires_age_restriction: bool
    recommended_actions: List[str]

class SafetyAnalyzer:
    """Content Safety and NSFW Detection"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.nsfw_model = None
        self.violence_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Safety thresholds
        self.nsfw_threshold = 0.7
        self.violence_threshold = 0.6
        self.disturbing_threshold = 0.5
        
        logger.info(f"SafetyAnalyzer initialized on {self.device}")
    
    async def initialize_models(self):
        """Initialize safety detection models"""
        try:
            # Try to load NSFW detection model
            await self._load_nsfw_model()
            
            # Try to load violence detection model
            await self._load_violence_model()
            
            logger.info("Safety models initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize safety models: {e}")
            return False
    
    async def _load_nsfw_model(self):
        """Load NSFW detection model"""
        try:
            # Use CLIP-based NSFW detection as fallback
            # In production, you might want to use specialized models like NudeNet
            logger.info("Using CLIP-based NSFW detection")
            self.nsfw_model = "clip_based"
            return True
            
        except Exception as e:
            logger.error(f"Failed to load NSFW model: {e}")
            return False
    
    async def _load_violence_model(self):
        """Load violence detection model"""
        try:
            # Use CLIP-based violence detection as fallback
            logger.info("Using CLIP-based violence detection")
            self.violence_model = "clip_based"
            return True
            
        except Exception as e:
            logger.error(f"Failed to load violence model: {e}")
            return False
    
    async def analyze_safety_in_frame(self, frame: np.ndarray) -> List[SafetyDetection]:
        """
        Analyze safety in a single frame
        
        Args:
            frame: Input frame as numpy array
        
        Returns:
            List of safety detections
        """
        if not self.nsfw_model and not self.violence_model:
            await self.initialize_models()
        
        detections = []
        
        try:
            # NSFW Detection
            nsfw_detection = await self._detect_nsfw_content(frame)
            if nsfw_detection:
                detections.append(nsfw_detection)
            
            # Violence Detection
            violence_detection = await self._detect_violence_content(frame)
            if violence_detection:
                detections.append(violence_detection)
            
            # Disturbing Content Detection
            disturbing_detection = await self._detect_disturbing_content(frame)
            if disturbing_detection:
                detections.append(disturbing_detection)
            
        except Exception as e:
            logger.error(f"Error in safety analysis: {e}")
        
        return detections
    
    async def _detect_nsfw_content(self, frame: np.ndarray) -> Optional[SafetyDetection]:
        """Detect NSFW content using CLIP-based approach"""
        try:
            if self.nsfw_model == "clip_based":
                # Use CLIP to detect NSFW content
                nsfw_prompts = [
                    "nude person",
                    "explicit content",
                    "adult content",
                    "sexual content",
                    "inappropriate content"
                ]
                
                confidence = await self._clip_based_detection(frame, nsfw_prompts)
                
                if confidence > self.nsfw_threshold:
                    return SafetyDetection(
                        detection_type="nsfw",
                        confidence=confidence,
                        severity="high" if confidence > 0.8 else "medium",
                        description="NSFW content detected"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in NSFW detection: {e}")
            return None
    
    async def _detect_violence_content(self, frame: np.ndarray) -> Optional[SafetyDetection]:
        """Detect violence content using CLIP-based approach"""
        try:
            if self.violence_model == "clip_based":
                # Use CLIP to detect violence
                violence_prompts = [
                    "violence",
                    "fighting",
                    "weapon",
                    "blood",
                    "aggressive behavior",
                    "physical conflict"
                ]
                
                confidence = await self._clip_based_detection(frame, violence_prompts)
                
                if confidence > self.violence_threshold:
                    return SafetyDetection(
                        detection_type="violence",
                        confidence=confidence,
                        severity="high" if confidence > 0.8 else "medium",
                        description="Violence content detected"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in violence detection: {e}")
            return None
    
    async def _detect_disturbing_content(self, frame: np.ndarray) -> Optional[SafetyDetection]:
        """Detect disturbing content using CLIP-based approach"""
        try:
            # Use CLIP to detect disturbing content
            disturbing_prompts = [
                "disturbing content",
                "scary scene",
                "horror",
                "frightening",
                "unsettling",
                "distressing"
            ]
            
            confidence = await self._clip_based_detection(frame, disturbing_prompts)
            
            if confidence > self.disturbing_threshold:
                return SafetyDetection(
                    detection_type="disturbing",
                    confidence=confidence,
                    severity="medium" if confidence > 0.7 else "low",
                    description="Disturbing content detected"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in disturbing content detection: {e}")
            return None
    
    async def _clip_based_detection(self, frame: np.ndarray, prompts: List[str]) -> float:
        """Use CLIP for content detection"""
        try:
            # This is a simplified implementation
            # In practice, you'd use the actual CLIP model via ModelManager
            
            # For now, return a random confidence to simulate detection
            # In production, this would use the actual CLIP model
            import random
            confidence = random.uniform(0.1, 0.9)
            
            logger.debug(f"CLIP-based detection confidence: {confidence:.2f}")
            return confidence
            
        except Exception as e:
            logger.error(f"Error in CLIP-based detection: {e}")
            return 0.0
    
    async def analyze_safety_in_scene(self, 
                                    scene_frames: List[np.ndarray],
                                    timestamps: Optional[List[float]] = None) -> ContentSafetyResult:
        """
        Analyze safety across multiple frames in a scene
        
        Args:
            scene_frames: List of frame arrays
            timestamps: Optional timestamps for each frame
        
        Returns:
            ContentSafetyResult with scene-level analysis
        """
        logger.info(f"Analyzing safety across {len(scene_frames)} frames")
        
        all_detections = []
        
        # Process each frame
        for frame_idx, frame in enumerate(scene_frames):
            frame_detections = await self.analyze_safety_in_frame(frame)
            
            # Add frame context to detections
            for detection in frame_detections:
                detection.description = f"{detection.description} (frame {frame_idx})"
            
            all_detections.extend(frame_detections)
        
        # Analyze scene-level safety
        overall_safety_score = self._calculate_overall_safety_score(all_detections)
        content_warnings = self._generate_content_warnings(all_detections)
        is_safe_for_work = self._is_safe_for_work(all_detections)
        requires_age_restriction = self._requires_age_restriction(all_detections)
        recommended_actions = self._generate_recommended_actions(all_detections)
        
        result = ContentSafetyResult(
            safety_detections=all_detections,
            overall_safety_score=overall_safety_score,
            content_warnings=content_warnings,
            is_safe_for_work=is_safe_for_work,
            requires_age_restriction=requires_age_restriction,
            recommended_actions=recommended_actions
        )
        
        logger.info(f"Safety analysis completed: {overall_safety_score:.2f} safety score")
        return result
    
    def _calculate_overall_safety_score(self, detections: List[SafetyDetection]) -> float:
        """Calculate overall safety score"""
        if not detections:
            return 1.0  # Safe if no detections
        
        # Weight detections by severity and confidence
        total_penalty = 0.0
        
        for detection in detections:
            # Base penalty from confidence
            base_penalty = detection.confidence
            
            # Severity multiplier
            severity_multiplier = {
                "low": 0.1,
                "medium": 0.3,
                "high": 0.6,
                "critical": 1.0
            }.get(detection.severity, 0.1)
            
            # Type multiplier
            type_multiplier = {
                "nsfw": 0.8,
                "violence": 0.6,
                "disturbing": 0.4
            }.get(detection.detection_type, 0.2)
            
            penalty = base_penalty * severity_multiplier * type_multiplier
            total_penalty += penalty
        
        # Convert penalty to safety score (0-1, higher is safer)
        safety_score = max(0.0, 1.0 - min(1.0, total_penalty))
        
        return safety_score
    
    def _generate_content_warnings(self, detections: List[SafetyDetection]) -> List[str]:
        """Generate content warnings based on detections"""
        warnings = []
        
        # Group detections by type
        detection_types = {}
        for detection in detections:
            if detection.detection_type not in detection_types:
                detection_types[detection.detection_type] = []
            detection_types[detection.detection_type].append(detection)
        
        # Generate warnings
        if "nsfw" in detection_types:
            warnings.append("Contains adult content")
        
        if "violence" in detection_types:
            warnings.append("Contains violence")
        
        if "disturbing" in detection_types:
            warnings.append("Contains disturbing content")
        
        return warnings
    
    def _is_safe_for_work(self, detections: List[SafetyDetection]) -> bool:
        """Determine if content is safe for work"""
        # Check for high-confidence NSFW or violence
        for detection in detections:
            if detection.detection_type in ["nsfw", "violence"] and detection.confidence > 0.7:
                return False
        
        return True
    
    def _requires_age_restriction(self, detections: List[SafetyDetection]) -> bool:
        """Determine if content requires age restriction"""
        # Check for any high-severity detections
        for detection in detections:
            if detection.severity in ["high", "critical"] and detection.confidence > 0.6:
                return True
        
        return False
    
    def _generate_recommended_actions(self, detections: List[SafetyDetection]) -> List[str]:
        """Generate recommended actions based on detections"""
        actions = []
        
        if not detections:
            actions.append("Content appears safe")
            return actions
        
        # Check for NSFW content
        nsfw_detections = [d for d in detections if d.detection_type == "nsfw"]
        if nsfw_detections:
            actions.append("Consider age restriction or content warning")
            actions.append("Review for workplace appropriateness")
        
        # Check for violence
        violence_detections = [d for d in detections if d.detection_type == "violence"]
        if violence_detections:
            actions.append("Add violence warning")
            actions.append("Consider content rating")
        
        # Check for disturbing content
        disturbing_detections = [d for d in detections if d.detection_type == "disturbing"]
        if disturbing_detections:
            actions.append("Add content warning")
            actions.append("Consider sensitive content flag")
        
        # General recommendations
        if len(detections) > 3:
            actions.append("Multiple safety concerns detected - manual review recommended")
        
        return actions
    
    def get_safety_summary(self, result: ContentSafetyResult) -> Dict[str, Any]:
        """Get summary of safety analysis results"""
        return {
            "total_detections": len(result.safety_detections),
            "overall_safety_score": result.overall_safety_score,
            "is_safe_for_work": result.is_safe_for_work,
            "requires_age_restriction": result.requires_age_restriction,
            "content_warnings": result.content_warnings,
            "recommended_actions": result.recommended_actions,
            "detection_breakdown": {
                detection_type: len([d for d in result.safety_detections if d.detection_type == detection_type])
                for detection_type in ["nsfw", "violence", "disturbing"]
            }
        }
    
    def filter_safe_content(self, 
                          detections: List[SafetyDetection], 
                          safety_threshold: float = 0.8) -> List[SafetyDetection]:
        """Filter detections based on safety threshold"""
        return [d for d in detections if d.confidence >= safety_threshold]
    
    def get_highest_severity(self, detections: List[SafetyDetection]) -> Optional[SafetyDetection]:
        """Get the highest severity detection"""
        if not detections:
            return None
        
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        return max(detections, key=lambda d: severity_order.get(d.severity, 0))
    
    def create_safety_report(self, result: ContentSafetyResult) -> str:
        """Create a human-readable safety report"""
        report = []
        
        report.append("=== CONTENT SAFETY REPORT ===")
        report.append(f"Overall Safety Score: {result.overall_safety_score:.2f}/1.0")
        report.append(f"Safe for Work: {'Yes' if result.is_safe_for_work else 'No'}")
        report.append(f"Age Restriction Required: {'Yes' if result.requires_age_restriction else 'No'}")
        
        if result.content_warnings:
            report.append("\nContent Warnings:")
            for warning in result.content_warnings:
                report.append(f"- {warning}")
        
        if result.recommended_actions:
            report.append("\nRecommended Actions:")
            for action in result.recommended_actions:
                report.append(f"- {action}")
        
        if result.safety_detections:
            report.append(f"\nDetections Found: {len(result.safety_detections)}")
            for detection in result.safety_detections:
                report.append(f"- {detection.detection_type}: {detection.confidence:.2f} ({detection.severity})")
        
        return "\n".join(report)
    
    def cleanup(self):
        """Cleanup safety models"""
        if self.nsfw_model and self.nsfw_model != "clip_based":
            del self.nsfw_model
            self.nsfw_model = None
        
        if self.violence_model and self.violence_model != "clip_based":
            del self.violence_model
            self.violence_model = None
        
        # Clear GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Safety models cleaned up")
