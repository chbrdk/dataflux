#!/usr/bin/env python3
"""
Action Recognition mit CLIP-based classification
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import cv2
import torch

logger = logging.getLogger(__name__)

@dataclass
class ActionDetection:
    """Ein erkanntes Action/Activity"""
    action_name: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x1, y1, x2, y2
    person_id: Optional[int] = None
    timestamp: Optional[float] = None
    context: Optional[str] = None

@dataclass
class ActionRecognitionResult:
    """Ergebnis der Action Recognition Analyse"""
    actions: List[ActionDetection]
    scene_activities: List[str]
    dominant_activity: Optional[str]
    activity_timeline: List[Dict[str, Any]]
    confidence_score: float

class ActionRecognizer:
    """CLIP-based Action Recognition"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.clip_model = None
        self.clip_processor = None
        
        # Action categories and prompts
        self.action_categories = {
            "body_posture": [
                "person standing",
                "person sitting", 
                "person lying down",
                "person crouching",
                "person kneeling"
            ],
            "movement": [
                "person walking",
                "person running",
                "person jumping",
                "person climbing",
                "person falling"
            ],
            "hand_gestures": [
                "person waving",
                "person pointing",
                "person clapping",
                "person giving thumbs up",
                "person shaking hands"
            ],
            "activities": [
                "person eating",
                "person drinking",
                "person talking",
                "person reading",
                "person writing",
                "person cooking",
                "person cleaning",
                "person exercising",
                "person dancing",
                "person playing sports"
            ],
            "interactions": [
                "person hugging",
                "person kissing",
                "person shaking hands",
                "person fighting",
                "person helping someone"
            ]
        }
        
        # Flatten all actions for easier processing
        self.all_actions = []
        for category, actions in self.action_categories.items():
            self.all_actions.extend(actions)
        
        logger.info(f"ActionRecognizer initialized with {len(self.all_actions)} action categories")
    
    async def initialize_model(self):
        """Initialize CLIP model for action recognition"""
        if not self.model_manager:
            logger.error("ModelManager not provided")
            return False
        
        try:
            # Load CLIP model via ModelManager
            async with self.model_manager.load("clip") as clip_model:
                self.clip_model = clip_model
                
                # Get processor
                if hasattr(clip_model, 'processor'):
                    self.clip_processor = clip_model.processor
                else:
                    # Fallback: try to get processor from transformers
                    try:
                        from transformers import CLIPProcessor
                        model_name = "openai/clip-vit-base-patch32"  # Default
                        self.clip_processor = CLIPProcessor.from_pretrained(model_name)
                    except ImportError:
                        logger.warning("CLIP processor not available")
                        return False
                
                logger.info("CLIP model loaded for action recognition")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize CLIP model: {e}")
            return False
    
    async def recognize_actions_in_frame(self, 
                                       frame: np.ndarray,
                                       person_bboxes: Optional[List[Tuple[int, int, int, int]]] = None,
                                       timestamp: Optional[float] = None) -> List[ActionDetection]:
        """
        Recognize actions in a single frame
        
        Args:
            frame: Input frame as numpy array
            person_bboxes: Optional list of person bounding boxes
            timestamp: Optional timestamp for the frame
        
        Returns:
            List of detected actions
        """
        if not self.clip_model or not self.clip_processor:
            logger.warning("CLIP model not initialized")
            return []
        
        try:
            # Convert frame to PIL Image
            from PIL import Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # If person bboxes provided, crop to persons
            if person_bboxes:
                actions = []
                for i, bbox in enumerate(person_bboxes):
                    x1, y1, x2, y2 = bbox
                    person_crop = pil_image.crop((x1, y1, x2, y2))
                    
                    person_actions = await self._analyze_person_actions(
                        person_crop, bbox, i, timestamp
                    )
                    actions.extend(person_actions)
                
                return actions
            else:
                # Analyze entire frame
                return await self._analyze_person_actions(
                    pil_image, None, None, timestamp
                )
                
        except Exception as e:
            logger.error(f"Error in action recognition: {e}")
            return []
    
    async def _analyze_person_actions(self, 
                                    image, 
                                    bbox: Optional[Tuple[int, int, int, int]],
                                    person_id: Optional[int],
                                    timestamp: Optional[float]) -> List[ActionDetection]:
        """Analyze actions for a person crop or entire image"""
        try:
            # Prepare inputs for CLIP
            inputs = self.clip_processor(
                text=self.all_actions,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            # Get model predictions
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=-1)
            
            # Convert to numpy
            probs_np = probs.cpu().numpy()[0]
            
            # Filter actions with confidence > threshold
            confidence_threshold = 0.3
            detected_actions = []
            
            for i, (action, confidence) in enumerate(zip(self.all_actions, probs_np)):
                if confidence > confidence_threshold:
                    # Determine context based on action category
                    context = self._get_action_context(action)
                    
                    action_detection = ActionDetection(
                        action_name=action,
                        confidence=float(confidence),
                        bbox=bbox,
                        person_id=person_id,
                        timestamp=timestamp,
                        context=context
                    )
                    detected_actions.append(action_detection)
            
            # Sort by confidence
            detected_actions.sort(key=lambda x: x.confidence, reverse=True)
            
            # Return top 3 actions per person
            return detected_actions[:3]
            
        except Exception as e:
            logger.error(f"Error analyzing person actions: {e}")
            return []
    
    def _get_action_context(self, action: str) -> str:
        """Get context category for an action"""
        for category, actions in self.action_categories.items():
            if action in actions:
                return category
        return "unknown"
    
    async def recognize_actions_in_scene(self, 
                                       scene_frames: List[np.ndarray],
                                       scene_person_bboxes: Optional[List[List[Tuple[int, int, int, int]]]] = None,
                                       timestamps: Optional[List[float]] = None) -> ActionRecognitionResult:
        """
        Recognize actions across multiple frames in a scene
        
        Args:
            scene_frames: List of frame arrays
            scene_person_bboxes: Optional list of person bbox lists for each frame
            timestamps: Optional timestamps for each frame
        
        Returns:
            ActionRecognitionResult with scene-level analysis
        """
        if not self.clip_model:
            await self.initialize_model()
        
        if not self.clip_model:
            logger.error("Failed to initialize CLIP model")
            return ActionRecognitionResult(
                actions=[],
                scene_activities=[],
                dominant_activity=None,
                activity_timeline=[],
                confidence_score=0.0
            )
        
        logger.info(f"Recognizing actions across {len(scene_frames)} frames")
        
        all_actions = []
        activity_timeline = []
        
        # Process each frame
        for frame_idx, frame in enumerate(scene_frames):
            person_bboxes = scene_person_bboxes[frame_idx] if scene_person_bboxes else None
            timestamp = timestamps[frame_idx] if timestamps else None
            
            frame_actions = await self.recognize_actions_in_frame(
                frame, person_bboxes, timestamp
            )
            
            all_actions.extend(frame_actions)
            
            # Add to timeline
            if frame_actions:
                timeline_entry = {
                    "frame_idx": frame_idx,
                    "timestamp": timestamp,
                    "actions": [
                        {
                            "action": action.action_name,
                            "confidence": action.confidence,
                            "person_id": action.person_id,
                            "context": action.context
                        }
                        for action in frame_actions
                    ]
                }
                activity_timeline.append(timeline_entry)
        
        # Analyze scene-level activities
        scene_activities = self._analyze_scene_activities(all_actions)
        dominant_activity = self._get_dominant_activity(all_actions)
        confidence_score = self._calculate_confidence_score(all_actions)
        
        result = ActionRecognitionResult(
            actions=all_actions,
            scene_activities=scene_activities,
            dominant_activity=dominant_activity,
            activity_timeline=activity_timeline,
            confidence_score=confidence_score
        )
        
        logger.info(f"Action recognition completed: {len(all_actions)} actions detected")
        return result
    
    def _analyze_scene_activities(self, actions: List[ActionDetection]) -> List[str]:
        """Analyze scene-level activities from individual actions"""
        if not actions:
            return []
        
        # Count actions by context
        context_counts = {}
        for action in actions:
            context = action.context
            if context not in context_counts:
                context_counts[context] = 0
            context_counts[context] += 1
        
        # Get most common contexts
        sorted_contexts = sorted(
            context_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [context for context, count in sorted_contexts[:3]]
    
    def _get_dominant_activity(self, actions: List[ActionDetection]) -> Optional[str]:
        """Get the dominant activity in the scene"""
        if not actions:
            return None
        
        # Count actions by name
        action_counts = {}
        for action in actions:
            name = action.action_name
            if name not in action_counts:
                action_counts[name] = 0
            action_counts[name] += 1
        
        # Get most common action
        if action_counts:
            dominant = max(action_counts.items(), key=lambda x: x[1])
            return dominant[0]
        
        return None
    
    def _calculate_confidence_score(self, actions: List[ActionDetection]) -> float:
        """Calculate overall confidence score for the scene"""
        if not actions:
            return 0.0
        
        # Average confidence of all actions
        avg_confidence = np.mean([action.confidence for action in actions])
        
        # Boost score if we have multiple consistent actions
        if len(actions) > 1:
            # Check for consistency (same action repeated)
            action_names = [action.action_name for action in actions]
            unique_actions = len(set(action_names))
            consistency_boost = 1.0 - (unique_actions / len(action_names)) * 0.2
            avg_confidence *= consistency_boost
        
        return min(1.0, avg_confidence)
    
    def get_action_summary(self, result: ActionRecognitionResult) -> Dict[str, Any]:
        """Get summary of action recognition results"""
        return {
            "total_actions_detected": len(result.actions),
            "scene_activities": result.scene_activities,
            "dominant_activity": result.dominant_activity,
            "confidence_score": result.confidence_score,
            "timeline_entries": len(result.activity_timeline),
            "action_distribution": {
                action.action_name: len([a for a in result.actions if a.action_name == action.action_name])
                for action in result.actions
            },
            "context_distribution": {
                action.context: len([a for a in result.actions if a.context == action.context])
                for action in result.actions
            }
        }
    
    def filter_actions_by_confidence(self, 
                                    actions: List[ActionDetection], 
                                    min_confidence: float = 0.5) -> List[ActionDetection]:
        """Filter actions by minimum confidence threshold"""
        return [action for action in actions if action.confidence >= min_confidence]
    
    def group_actions_by_person(self, actions: List[ActionDetection]) -> Dict[int, List[ActionDetection]]:
        """Group actions by person ID"""
        person_actions = {}
        
        for action in actions:
            person_id = action.person_id
            if person_id is not None:
                if person_id not in person_actions:
                    person_actions[person_id] = []
                person_actions[person_id].append(action)
        
        return person_actions
