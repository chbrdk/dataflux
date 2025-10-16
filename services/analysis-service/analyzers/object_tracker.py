#!/usr/bin/env python3
"""
Object Tracking mit ByteTrack für consistent IDs über Frames
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import cv2

logger = logging.getLogger(__name__)

@dataclass
class TrackedObject:
    """Ein getracktes Objekt mit konsistenter ID über Frames"""
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Tuple[float, float]
    velocity: Tuple[float, float]  # pixels per frame
    trajectory: List[Tuple[float, float]]  # historical positions
    first_seen_frame: int
    last_seen_frame: int
    age: int  # frames since first seen
    lost_count: int  # frames since last detection

@dataclass
class TrackingResult:
    """Ergebnis der Object Tracking Analyse"""
    tracked_objects: List[TrackedObject]
    trajectories: Dict[int, List[Tuple[float, float]]]
    movement_stats: Dict[str, Any]
    scene_movement_score: float

class ByteTracker:
    """ByteTrack Implementation für Object Tracking"""
    
    def __init__(self, 
                 track_thresh: float = 0.5,
                 track_buffer: int = 30,
                 match_thresh: float = 0.8,
                 frame_rate: int = 30):
        """
        Initialize ByteTracker
        
        Args:
            track_thresh: Detection confidence threshold for tracking
            track_buffer: Number of frames to keep lost tracks
            match_thresh: IoU threshold for track matching
            frame_rate: Video frame rate
        """
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate
        
        # Tracking state
        self.tracked_objects: Dict[int, TrackedObject] = {}
        self.next_track_id = 1
        self.frame_count = 0
        
        logger.info(f"ByteTracker initialized: thresh={track_thresh}, buffer={track_buffer}")
    
    def update(self, detections: List[Dict[str, Any]]) -> List[TrackedObject]:
        """
        Update tracker with new detections
        
        Args:
            detections: List of detection dictionaries with keys:
                - bbox: [x1, y1, x2, y2]
                - confidence: float
                - class_id: int
                - class_name: str
        
        Returns:
            List of tracked objects
        """
        self.frame_count += 1
        
        # Filter detections by confidence
        valid_detections = [
            det for det in detections 
            if det['confidence'] >= self.track_thresh
        ]
        
        if not valid_detections:
            # No detections, update lost counts
            self._update_lost_tracks()
            return list(self.tracked_objects.values())
        
        # Convert detections to numpy arrays for matching
        detection_boxes = np.array([det['bbox'] for det in valid_detections])
        detection_scores = np.array([det['confidence'] for det in valid_detections])
        
        # Get existing track boxes
        if self.tracked_objects:
            track_boxes = np.array([
                obj.bbox for obj in self.tracked_objects.values()
            ])
            track_ids = list(self.tracked_objects.keys())
        else:
            track_boxes = np.array([])
            track_ids = []
        
        # Match detections to existing tracks
        if len(track_boxes) > 0 and len(detection_boxes) > 0:
            matches, unmatched_dets, unmatched_tracks = self._associate_detections_to_trackers(
                detection_boxes, track_boxes, detection_scores
            )
        else:
            matches = []
            unmatched_dets = list(range(len(detection_boxes)))
            unmatched_tracks = list(range(len(track_boxes)))
        
        # Update matched tracks
        for det_idx, track_idx in matches:
            track_id = track_ids[track_idx]
            detection = valid_detections[det_idx]
            
            self._update_track(track_id, detection)
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            detection = valid_detections[det_idx]
            self._create_new_track(detection)
        
        # Mark unmatched tracks as lost
        for track_idx in unmatched_tracks:
            track_id = track_ids[track_idx]
            self.tracked_objects[track_id].lost_count += 1
        
        # Remove lost tracks
        self._remove_lost_tracks()
        
        return list(self.tracked_objects.values())
    
    def _associate_detections_to_trackers(self, 
                                        detections: np.ndarray, 
                                        trackers: np.ndarray,
                                        detection_scores: np.ndarray) -> Tuple[List, List, List]:
        """Associate detections to trackers using IoU"""
        if len(detections) == 0 or len(trackers) == 0:
            return [], list(range(len(detections))), list(range(len(trackers)))
        
        # Calculate IoU matrix
        iou_matrix = self._calculate_iou_matrix(detections, trackers)
        
        # Hungarian algorithm for optimal assignment
        matches, unmatched_dets, unmatched_tracks = self._hungarian_assignment(
            iou_matrix, detection_scores
        )
        
        return matches, unmatched_dets, unmatched_tracks
    
    def _calculate_iou_matrix(self, boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """Calculate IoU matrix between two sets of boxes"""
        def box_area(box):
            return (box[2] - box[0]) * (box[3] - box[1])
        
        area1 = np.array([box_area(box) for box in boxes1])
        area2 = np.array([box_area(box) for box in boxes2])
        
        # Calculate intersection
        lt = np.maximum(boxes1[:, None, :2], boxes2[:, :2])  # [N, M, 2]
        rb = np.minimum(boxes1[:, None, 2:], boxes2[:, 2:])  # [N, M, 2]
        
        wh = np.maximum(rb - lt, 0)  # [N, M, 2]
        inter = wh[:, :, 0] * wh[:, :, 1]  # [N, M]
        
        # Calculate union
        union = area1[:, None] + area2 - inter
        
        # Calculate IoU
        iou = inter / union
        return iou
    
    def _hungarian_assignment(self, 
                            iou_matrix: np.ndarray, 
                            detection_scores: np.ndarray) -> Tuple[List, List, List]:
        """Hungarian algorithm for optimal assignment"""
        # Simple greedy assignment for now
        # In production, use scipy.optimize.linear_sum_assignment
        
        matches = []
        unmatched_dets = list(range(len(iou_matrix)))
        unmatched_tracks = list(range(len(iou_matrix[0])))
        
        # Sort by IoU score
        det_indices, track_indices = np.where(iou_matrix >= self.match_thresh)
        scores = iou_matrix[det_indices, track_indices]
        
        # Sort by score (descending)
        sorted_indices = np.argsort(-scores)
        
        used_dets = set()
        used_tracks = set()
        
        for idx in sorted_indices:
            det_idx = det_indices[idx]
            track_idx = track_indices[idx]
            
            if det_idx not in used_dets and track_idx not in used_tracks:
                matches.append([det_idx, track_idx])
                used_dets.add(det_idx)
                used_tracks.add(track_idx)
        
        # Update unmatched lists
        unmatched_dets = [i for i in unmatched_dets if i not in used_dets]
        unmatched_tracks = [i for i in unmatched_tracks if i not in used_tracks]
        
        return matches, unmatched_dets, unmatched_tracks
    
    def _update_track(self, track_id: int, detection: Dict[str, Any]):
        """Update existing track with new detection"""
        obj = self.tracked_objects[track_id]
        
        # Calculate velocity
        old_center = obj.center
        new_bbox = detection['bbox']
        new_center = (
            (new_bbox[0] + new_bbox[2]) / 2,
            (new_bbox[1] + new_bbox[3]) / 2
        )
        
        velocity = (
            new_center[0] - old_center[0],
            new_center[1] - old_center[1]
        )
        
        # Update track
        obj.bbox = tuple(new_bbox)
        obj.center = new_center
        obj.velocity = velocity
        obj.confidence = detection['confidence']
        obj.trajectory.append(new_center)
        obj.last_seen_frame = self.frame_count
        obj.age = self.frame_count - obj.first_seen_frame
        obj.lost_count = 0
        
        # Keep trajectory within reasonable length
        if len(obj.trajectory) > 100:
            obj.trajectory = obj.trajectory[-50:]
    
    def _create_new_track(self, detection: Dict[str, Any]):
        """Create new track from detection"""
        bbox = detection['bbox']
        center = (
            (bbox[0] + bbox[2]) / 2,
            (bbox[1] + bbox[3]) / 2
        )
        
        tracked_obj = TrackedObject(
            track_id=self.next_track_id,
            class_id=detection['class_id'],
            class_name=detection['class_name'],
            confidence=detection['confidence'],
            bbox=tuple(bbox),
            center=center,
            velocity=(0.0, 0.0),
            trajectory=[center],
            first_seen_frame=self.frame_count,
            last_seen_frame=self.frame_count,
            age=0,
            lost_count=0
        )
        
        self.tracked_objects[self.next_track_id] = tracked_obj
        self.next_track_id += 1
    
    def _update_lost_tracks(self):
        """Update lost tracks (no detections)"""
        for obj in self.tracked_objects.values():
            obj.lost_count += 1
    
    def _remove_lost_tracks(self):
        """Remove tracks that have been lost for too long"""
        tracks_to_remove = []
        
        for track_id, obj in self.tracked_objects.items():
            if obj.lost_count > self.track_buffer:
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracked_objects[track_id]
            logger.debug(f"Removed lost track {track_id}")
    
    def get_trajectories(self) -> Dict[int, List[Tuple[float, float]]]:
        """Get all trajectories"""
        return {
            track_id: obj.trajectory 
            for track_id, obj in self.tracked_objects.items()
        }
    
    def get_movement_stats(self) -> Dict[str, Any]:
        """Get movement statistics"""
        if not self.tracked_objects:
            return {}
        
        velocities = [obj.velocity for obj in self.tracked_objects.values()]
        speeds = [np.sqrt(v[0]**2 + v[1]**2) for v in velocities]
        
        return {
            "total_tracks": len(self.tracked_objects),
            "active_tracks": len([obj for obj in self.tracked_objects.values() if obj.lost_count == 0]),
            "average_speed": np.mean(speeds) if speeds else 0.0,
            "max_speed": np.max(speeds) if speeds else 0.0,
            "total_distance": sum(len(obj.trajectory) for obj in self.tracked_objects.values())
        }

class ObjectTracker:
    """Main Object Tracker class"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.byte_tracker = None
        self.frame_rate = 30
        
        logger.info("ObjectTracker initialized")
    
    async def initialize_tracker(self, frame_rate: int = 30):
        """Initialize the ByteTracker"""
        self.frame_rate = frame_rate
        self.byte_tracker = ByteTracker(frame_rate=frame_rate)
        logger.info(f"ByteTracker initialized with frame rate: {frame_rate}")
    
    async def track_objects_in_scene(self, 
                                   scene_frames: List[np.ndarray],
                                   scene_detections: List[List[Dict[str, Any]]]) -> TrackingResult:
        """
        Track objects across frames in a scene
        
        Args:
            scene_frames: List of frame arrays
            scene_detections: List of detection lists for each frame
        
        Returns:
            TrackingResult with tracked objects and trajectories
        """
        if not self.byte_tracker:
            await self.initialize_tracker()
        
        logger.info(f"Tracking objects across {len(scene_frames)} frames")
        
        # Process each frame
        for frame_idx, (frame, detections) in enumerate(zip(scene_frames, scene_detections)):
            tracked_objects = self.byte_tracker.update(detections)
            
            if frame_idx % 10 == 0:  # Log every 10th frame
                logger.debug(f"Frame {frame_idx}: {len(tracked_objects)} tracked objects")
        
        # Get final results
        tracked_objects = list(self.byte_tracker.tracked_objects.values())
        trajectories = self.byte_tracker.get_trajectories()
        movement_stats = self.byte_tracker.get_movement_stats()
        
        # Calculate scene movement score
        scene_movement_score = self._calculate_scene_movement_score(tracked_objects)
        
        result = TrackingResult(
            tracked_objects=tracked_objects,
            trajectories=trajectories,
            movement_stats=movement_stats,
            scene_movement_score=scene_movement_score
        )
        
        logger.info(f"Tracking completed: {len(tracked_objects)} objects tracked")
        return result
    
    def _calculate_scene_movement_score(self, tracked_objects: List[TrackedObject]) -> float:
        """Calculate overall movement score for the scene"""
        if not tracked_objects:
            return 0.0
        
        # Calculate average speed and trajectory length
        speeds = []
        trajectory_lengths = []
        
        for obj in tracked_objects:
            if len(obj.trajectory) > 1:
                # Calculate average speed
                total_distance = 0.0
                for i in range(1, len(obj.trajectory)):
                    dx = obj.trajectory[i][0] - obj.trajectory[i-1][0]
                    dy = obj.trajectory[i][1] - obj.trajectory[i-1][1]
                    total_distance += np.sqrt(dx**2 + dy**2)
                
                avg_speed = total_distance / len(obj.trajectory) if len(obj.trajectory) > 0 else 0.0
                speeds.append(avg_speed)
                trajectory_lengths.append(len(obj.trajectory))
        
        if not speeds:
            return 0.0
        
        # Normalize scores (0-1)
        avg_speed = np.mean(speeds)
        avg_trajectory_length = np.mean(trajectory_lengths)
        
        # Combine metrics
        movement_score = min(1.0, (avg_speed / 50.0) + (avg_trajectory_length / 100.0))
        
        return movement_score
    
    def reset_tracker(self):
        """Reset tracker for new video/scene"""
        if self.byte_tracker:
            self.byte_tracker = ByteTracker(frame_rate=self.frame_rate)
            logger.info("Tracker reset for new scene")
    
    def get_tracking_summary(self, result: TrackingResult) -> Dict[str, Any]:
        """Get summary of tracking results"""
        return {
            "total_objects_tracked": len(result.tracked_objects),
            "active_tracks": len([obj for obj in result.tracked_objects if obj.lost_count == 0]),
            "total_trajectories": len(result.trajectories),
            "scene_movement_score": result.scene_movement_score,
            "movement_stats": result.movement_stats,
            "object_types": {
                obj.class_name: len([o for o in result.tracked_objects if o.class_name == obj.class_name])
                for obj in result.tracked_objects
            }
        }
