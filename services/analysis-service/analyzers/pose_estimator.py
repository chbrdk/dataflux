#!/usr/bin/env python3
"""
Pose Estimation mit MediaPipe (Pro-Tier only)
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import mediapipe as mp

logger = logging.getLogger(__name__)

@dataclass
class PoseLandmark:
    """Ein Pose Landmark"""
    x: float
    y: float
    z: float
    visibility: float

@dataclass
class PoseEstimation:
    """Pose Estimation Result"""
    person_id: int
    body_landmarks: List[PoseLandmark]  # 33 body landmarks
    left_hand_landmarks: Optional[List[PoseLandmark]] = None  # 21 hand landmarks
    right_hand_landmarks: Optional[List[PoseLandmark]] = None  # 21 hand landmarks
    face_landmarks: Optional[List[PoseLandmark]] = None  # 468 face landmarks
    confidence: float = 0.0
    pose_classification: Optional[str] = None

@dataclass
class PoseAnalysisResult:
    """Complete Pose Analysis Result"""
    poses: List[PoseEstimation]
    scene_pose_summary: Dict[str, Any]
    dominant_poses: List[str]
    pose_timeline: List[Dict[str, Any]]

class PoseEstimator:
    """MediaPipe-based Pose Estimation"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.holistic = None
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_holistic = mp.solutions.holistic
        
        # Pose classification categories
        self.pose_categories = {
            "standing": ["person standing upright", "person in standing position"],
            "sitting": ["person sitting", "person in seated position"],
            "lying": ["person lying down", "person in prone position"],
            "crouching": ["person crouching", "person in squat position"],
            "walking": ["person walking", "person in walking motion"],
            "running": ["person running", "person in running motion"],
            "dancing": ["person dancing", "person in dance pose"],
            "exercising": ["person exercising", "person in workout pose"]
        }
        
        logger.info("PoseEstimator initialized")
    
    async def initialize_model(self):
        """Initialize MediaPipe Holistic model"""
        try:
            self.holistic = self.mp_holistic.Holistic(
                static_image_mode=False,
                model_complexity=2,  # Highest accuracy
                enable_segmentation=False,
                refine_face_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe Holistic model initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe model: {e}")
            return False
    
    async def estimate_pose_in_frame(self, 
                                   frame: np.ndarray,
                                   person_id: int = 0) -> Optional[PoseEstimation]:
        """
        Estimate pose in a single frame
        
        Args:
            frame: Input frame as numpy array
            person_id: ID of the person (for multi-person scenarios)
        
        Returns:
            PoseEstimation object or None if no pose detected
        """
        if not self.holistic:
            await self.initialize_model()
        
        if not self.holistic:
            logger.warning("MediaPipe model not initialized")
            return None
        
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame
            results = self.holistic.process(rgb_frame)
            
            # Extract landmarks
            pose_estimation = self._extract_landmarks(results, person_id)
            
            if pose_estimation:
                # Classify pose
                pose_classification = await self._classify_pose(pose_estimation)
                pose_estimation.pose_classification = pose_classification
            
            return pose_estimation
            
        except Exception as e:
            logger.error(f"Error in pose estimation: {e}")
            return None
    
    def _extract_landmarks(self, results, person_id: int) -> Optional[PoseEstimation]:
        """Extract landmarks from MediaPipe results"""
        try:
            # Check if pose landmarks are detected
            if not results.pose_landmarks:
                return None
            
            # Extract body landmarks (33 points)
            body_landmarks = []
            for landmark in results.pose_landmarks.landmark:
                body_landmarks.append(PoseLandmark(
                    x=landmark.x,
                    y=landmark.y,
                    z=landmark.z,
                    visibility=landmark.visibility
                ))
            
            # Extract hand landmarks (21 points each)
            left_hand_landmarks = None
            if results.left_hand_landmarks:
                left_hand_landmarks = []
                for landmark in results.left_hand_landmarks.landmark:
                    left_hand_landmarks.append(PoseLandmark(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z,
                        visibility=landmark.visibility
                    ))
            
            right_hand_landmarks = None
            if results.right_hand_landmarks:
                right_hand_landmarks = []
                for landmark in results.right_hand_landmarks.landmark:
                    right_hand_landmarks.append(PoseLandmark(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z,
                        visibility=landmark.visibility
                    ))
            
            # Extract face landmarks (468 points)
            face_landmarks = None
            if results.face_landmarks:
                face_landmarks = []
                for landmark in results.face_landmarks.landmark:
                    face_landmarks.append(PoseLandmark(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z,
                        visibility=landmark.visibility
                    ))
            
            # Calculate confidence based on landmark visibility
            confidence = self._calculate_pose_confidence(body_landmarks)
            
            return PoseEstimation(
                person_id=person_id,
                body_landmarks=body_landmarks,
                left_hand_landmarks=left_hand_landmarks,
                right_hand_landmarks=right_hand_landmarks,
                face_landmarks=face_landmarks,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error extracting landmarks: {e}")
            return None
    
    def _calculate_pose_confidence(self, body_landmarks: List[PoseLandmark]) -> float:
        """Calculate pose confidence based on landmark visibility"""
        if not body_landmarks:
            return 0.0
        
        # Average visibility of key landmarks
        key_landmarks = [0, 11, 12, 13, 14, 15, 16, 23, 24]  # Key body points
        visibilities = [body_landmarks[i].visibility for i in key_landmarks if i < len(body_landmarks)]
        
        if visibilities:
            return np.mean(visibilities)
        else:
            return 0.0
    
    async def _classify_pose(self, pose_estimation: PoseEstimation) -> Optional[str]:
        """Classify pose using simple heuristics"""
        try:
            body_landmarks = pose_estimation.body_landmarks
            
            if len(body_landmarks) < 33:
                return "unknown"
            
            # Get key landmarks
            nose = body_landmarks[0]
            left_shoulder = body_landmarks[11]
            right_shoulder = body_landmarks[12]
            left_hip = body_landmarks[23]
            right_hip = body_landmarks[24]
            left_ankle = body_landmarks[27]
            right_ankle = body_landmarks[28]
            
            # Calculate key angles and positions
            shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_center_y = (left_hip.y + right_hip.y) / 2
            ankle_center_y = (left_ankle.y + right_ankle.y) / 2
            
            # Simple pose classification based on landmark positions
            if ankle_center_y > hip_center_y + 0.1:  # Ankles below hips
                if shoulder_center_y < hip_center_y - 0.05:  # Shoulders above hips
                    return "standing"
                else:
                    return "sitting"
            elif hip_center_y > shoulder_center_y + 0.1:  # Hips below shoulders
                return "lying"
            else:
                return "crouching"
                
        except Exception as e:
            logger.error(f"Error classifying pose: {e}")
            return "unknown"
    
    async def estimate_poses_in_scene(self, 
                                    scene_frames: List[np.ndarray],
                                    timestamps: Optional[List[float]] = None) -> PoseAnalysisResult:
        """
        Estimate poses across multiple frames in a scene
        
        Args:
            scene_frames: List of frame arrays
            timestamps: Optional timestamps for each frame
        
        Returns:
            PoseAnalysisResult with scene-level analysis
        """
        if not self.holistic:
            await self.initialize_model()
        
        if not self.holistic:
            logger.error("MediaPipe model not initialized")
            return PoseAnalysisResult(
                poses=[],
                scene_pose_summary={},
                dominant_poses=[],
                pose_timeline=[]
            )
        
        logger.info(f"Estimating poses across {len(scene_frames)} frames")
        
        all_poses = []
        pose_timeline = []
        
        # Process each frame
        for frame_idx, frame in enumerate(scene_frames):
            timestamp = timestamps[frame_idx] if timestamps else None
            
            # Estimate pose for the frame
            pose_estimation = await self.estimate_pose_in_frame(frame, person_id=0)
            
            if pose_estimation:
                all_poses.append(pose_estimation)
                
                # Add to timeline
                timeline_entry = {
                    "frame_idx": frame_idx,
                    "timestamp": timestamp,
                    "pose_classification": pose_estimation.pose_classification,
                    "confidence": pose_estimation.confidence,
                    "has_hands": pose_estimation.left_hand_landmarks is not None or pose_estimation.right_hand_landmarks is not None,
                    "has_face": pose_estimation.face_landmarks is not None
                }
                pose_timeline.append(timeline_entry)
        
        # Analyze scene-level pose patterns
        scene_summary = self._analyze_scene_poses(all_poses)
        dominant_poses = self._get_dominant_poses(all_poses)
        
        result = PoseAnalysisResult(
            poses=all_poses,
            scene_pose_summary=scene_summary,
            dominant_poses=dominant_poses,
            pose_timeline=pose_timeline
        )
        
        logger.info(f"Pose estimation completed: {len(all_poses)} poses detected")
        return result
    
    def _analyze_scene_poses(self, poses: List[PoseEstimation]) -> Dict[str, Any]:
        """Analyze pose patterns in the scene"""
        if not poses:
            return {}
        
        # Count pose classifications
        pose_counts = {}
        confidences = []
        hand_detections = 0
        face_detections = 0
        
        for pose in poses:
            classification = pose.pose_classification
            if classification:
                pose_counts[classification] = pose_counts.get(classification, 0) + 1
            
            confidences.append(pose.confidence)
            
            if pose.left_hand_landmarks or pose.right_hand_landmarks:
                hand_detections += 1
            
            if pose.face_landmarks:
                face_detections += 1
        
        return {
            "total_poses": len(poses),
            "pose_distribution": pose_counts,
            "average_confidence": np.mean(confidences) if confidences else 0.0,
            "hand_detection_rate": hand_detections / len(poses) if poses else 0.0,
            "face_detection_rate": face_detections / len(poses) if poses else 0.0,
            "pose_stability": self._calculate_pose_stability(poses)
        }
    
    def _get_dominant_poses(self, poses: List[PoseEstimation]) -> List[str]:
        """Get dominant pose types in the scene"""
        pose_counts = {}
        
        for pose in poses:
            classification = pose.pose_classification
            if classification:
                pose_counts[classification] = pose_counts.get(classification, 0) + 1
        
        # Sort by count and return top 3
        sorted_poses = sorted(pose_counts.items(), key=lambda x: x[1], reverse=True)
        return [pose for pose, count in sorted_poses[:3]]
    
    def _calculate_pose_stability(self, poses: List[PoseEstimation]) -> float:
        """Calculate pose stability across frames"""
        if len(poses) < 2:
            return 1.0
        
        # Calculate pose changes between consecutive frames
        pose_changes = []
        
        for i in range(1, len(poses)):
            prev_pose = poses[i-1]
            curr_pose = poses[i]
            
            if prev_pose.body_landmarks and curr_pose.body_landmarks:
                # Calculate average landmark movement
                movements = []
                for j in range(min(len(prev_pose.body_landmarks), len(curr_pose.body_landmarks))):
                    prev_landmark = prev_pose.body_landmarks[j]
                    curr_landmark = curr_pose.body_landmarks[j]
                    
                    movement = np.sqrt(
                        (prev_landmark.x - curr_landmark.x)**2 +
                        (prev_landmark.y - curr_landmark.y)**2
                    )
                    movements.append(movement)
                
                avg_movement = np.mean(movements) if movements else 0.0
                pose_changes.append(avg_movement)
        
        if pose_changes:
            # Lower movement = higher stability
            avg_change = np.mean(pose_changes)
            stability = max(0.0, 1.0 - (avg_change * 10))  # Scale factor
            return stability
        
        return 1.0
    
    def get_pose_summary(self, result: PoseAnalysisResult) -> Dict[str, Any]:
        """Get summary of pose analysis results"""
        return {
            "total_poses_detected": len(result.poses),
            "dominant_poses": result.dominant_poses,
            "scene_summary": result.scene_pose_summary,
            "timeline_entries": len(result.pose_timeline),
            "average_confidence": np.mean([pose.confidence for pose in result.poses]) if result.poses else 0.0
        }
    
    def visualize_pose(self, frame: np.ndarray, pose_estimation: PoseEstimation) -> np.ndarray:
        """Visualize pose landmarks on frame"""
        if not pose_estimation:
            return frame
        
        annotated_frame = frame.copy()
        
        try:
            # Convert landmarks to MediaPipe format
            pose_landmarks = []
            if pose_estimation.body_landmarks:
                for landmark in pose_estimation.body_landmarks:
                    pose_landmarks.append(mp.framework.formats.landmark_pb2.NormalizedLandmark(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z,
                        visibility=landmark.visibility
                    ))
            
            # Draw pose landmarks
            if pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    pose_landmarks,
                    self.mp_holistic.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2)
                )
            
            # Add pose classification text
            if pose_estimation.pose_classification:
                cv2.putText(
                    annotated_frame,
                    f"Pose: {pose_estimation.pose_classification}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )
            
            # Add confidence text
            cv2.putText(
                annotated_frame,
                f"Confidence: {pose_estimation.confidence:.2f}",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
        except Exception as e:
            logger.error(f"Error visualizing pose: {e}")
        
        return annotated_frame
    
    def cleanup(self):
        """Cleanup MediaPipe resources"""
        if self.holistic:
            self.holistic.close()
            self.holistic = None
            logger.info("MediaPipe model cleaned up")
