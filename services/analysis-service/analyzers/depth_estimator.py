#!/usr/bin/env python3
"""
Depth Estimation mit Depth-Anything (Pro-Tier only)
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
class DepthMap:
    """Depth Map Result"""
    depth_array: np.ndarray  # Normalized 0-1 depth values
    min_depth: float
    max_depth: float
    model_used: str
    confidence: float = 0.0

@dataclass
class DepthAnalysisResult:
    """Complete Depth Analysis Result"""
    depth_maps: List[DepthMap]
    scene_depth_summary: Dict[str, Any]
    foreground_objects: List[Dict[str, Any]]
    background_regions: List[Dict[str, Any]]
    depth_visualization: Optional[np.ndarray] = None

class DepthEstimator:
    """Depth Estimation using Depth-Anything"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.depth_model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"DepthEstimator initialized on {self.device}")
    
    async def initialize_model(self):
        """Initialize Depth-Anything model"""
        try:
            from transformers import DPTForDepthEstimation, DPTImageProcessor
            
            # Load model and processor
            model_name = "Intel/dpt-large"  # High quality depth estimation
            self.processor = DPTImageProcessor.from_pretrained(model_name)
            self.depth_model = DPTForDepthEstimation.from_pretrained(model_name)
            
            # Move to device
            self.depth_model.to(self.device)
            self.depth_model.eval()
            
            logger.info(f"Depth-Anything model loaded: {model_name}")
            return True
            
        except ImportError:
            logger.error("transformers library not available for depth estimation")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize depth model: {e}")
            return False
    
    async def estimate_depth_in_frame(self, frame: np.ndarray) -> Optional[DepthMap]:
        """
        Estimate depth in a single frame
        
        Args:
            frame: Input frame as numpy array
        
        Returns:
            DepthMap object or None if estimation failed
        """
        if not self.depth_model or not self.processor:
            await self.initialize_model()
        
        if not self.depth_model or not self.processor:
            logger.warning("Depth model not initialized")
            return None
        
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            
            # Process image
            inputs = self.processor(images=pil_image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get depth prediction
            with torch.no_grad():
                outputs = self.depth_model(**inputs)
                predicted_depth = outputs.predicted_depth
            
            # Convert to numpy array
            depth_array = predicted_depth.cpu().numpy().squeeze()
            
            # Normalize depth values to 0-1 range
            min_depth = np.min(depth_array)
            max_depth = np.max(depth_array)
            
            if max_depth > min_depth:
                normalized_depth = (depth_array - min_depth) / (max_depth - min_depth)
            else:
                normalized_depth = np.zeros_like(depth_array)
            
            # Calculate confidence based on depth range
            depth_range = max_depth - min_depth
            confidence = min(1.0, depth_range / 10.0)  # Normalize confidence
            
            return DepthMap(
                depth_array=normalized_depth,
                min_depth=min_depth,
                max_depth=max_depth,
                model_used="Intel/dpt-large",
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in depth estimation: {e}")
            return None
    
    async def estimate_depth_in_scene(self, 
                                    scene_frames: List[np.ndarray],
                                    timestamps: Optional[List[float]] = None) -> DepthAnalysisResult:
        """
        Estimate depth across multiple frames in a scene
        
        Args:
            scene_frames: List of frame arrays
            timestamps: Optional timestamps for each frame
        
        Returns:
            DepthAnalysisResult with scene-level analysis
        """
        if not self.depth_model:
            await self.initialize_model()
        
        if not self.depth_model:
            logger.error("Depth model not initialized")
            return DepthAnalysisResult(
                depth_maps=[],
                scene_depth_summary={},
                foreground_objects=[],
                background_regions=[]
            )
        
        logger.info(f"Estimating depth across {len(scene_frames)} frames")
        
        depth_maps = []
        
        # Process each frame
        for frame_idx, frame in enumerate(scene_frames):
            depth_map = await self.estimate_depth_in_frame(frame)
            
            if depth_map:
                depth_maps.append(depth_map)
            
            if frame_idx % 10 == 0:  # Log every 10th frame
                logger.debug(f"Processed {frame_idx + 1}/{len(scene_frames)} frames")
        
        # Analyze scene-level depth patterns
        scene_summary = self._analyze_scene_depth(depth_maps)
        foreground_objects = self._extract_foreground_objects(depth_maps)
        background_regions = self._extract_background_regions(depth_maps)
        
        # Generate depth visualization
        depth_visualization = None
        if depth_maps:
            depth_visualization = self._create_depth_visualization(depth_maps[0])
        
        result = DepthAnalysisResult(
            depth_maps=depth_maps,
            scene_depth_summary=scene_summary,
            foreground_objects=foreground_objects,
            background_regions=background_regions,
            depth_visualization=depth_visualization
        )
        
        logger.info(f"Depth estimation completed: {len(depth_maps)} depth maps generated")
        return result
    
    def _analyze_scene_depth(self, depth_maps: List[DepthMap]) -> Dict[str, Any]:
        """Analyze depth patterns in the scene"""
        if not depth_maps:
            return {}
        
        # Calculate depth statistics
        all_depths = np.concatenate([dm.depth_array.flatten() for dm in depth_maps])
        
        depth_stats = {
            "total_depth_maps": len(depth_maps),
            "average_depth": np.mean(all_depths),
            "depth_std": np.std(all_depths),
            "min_depth": np.min(all_depths),
            "max_depth": np.max(all_depths),
            "depth_range": np.max(all_depths) - np.min(all_depths),
            "average_confidence": np.mean([dm.confidence for dm in depth_maps]),
            "depth_complexity": self._calculate_depth_complexity(depth_maps)
        }
        
        return depth_stats
    
    def _calculate_depth_complexity(self, depth_maps: List[DepthMap]) -> float:
        """Calculate depth complexity score"""
        if not depth_maps:
            return 0.0
        
        complexities = []
        
        for depth_map in depth_maps:
            # Calculate depth gradient magnitude
            depth_array = depth_map.depth_array
            
            # Calculate gradients
            grad_x = np.gradient(depth_array, axis=1)
            grad_y = np.gradient(depth_array, axis=0)
            
            # Calculate gradient magnitude
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Complexity is the mean gradient magnitude
            complexity = np.mean(gradient_magnitude)
            complexities.append(complexity)
        
        return np.mean(complexities)
    
    def _extract_foreground_objects(self, depth_maps: List[DepthMap]) -> List[Dict[str, Any]]:
        """Extract foreground objects based on depth"""
        if not depth_maps:
            return []
        
        foreground_objects = []
        
        for i, depth_map in enumerate(depth_maps):
            # Find regions with low depth values (closer to camera)
            foreground_threshold = 0.3  # Objects closer than 30% of max depth
            foreground_mask = depth_map.depth_array < foreground_threshold
            
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                foreground_mask.astype(np.uint8), connectivity=8
            )
            
            # Extract object information
            for label in range(1, num_labels):  # Skip background (label 0)
                area = stats[label, cv2.CC_STAT_AREA]
                
                if area > 100:  # Minimum object size
                    x, y, w, h = stats[label, cv2.CC_STAT_LEFT], stats[label, cv2.CC_STAT_TOP], \
                                stats[label, cv2.CC_STAT_WIDTH], stats[label, cv2.CC_STAT_HEIGHT]
                    
                    # Calculate average depth for this object
                    object_mask = labels == label
                    avg_depth = np.mean(depth_map.depth_array[object_mask])
                    
                    foreground_objects.append({
                        "frame_idx": i,
                        "bbox": (x, y, w, h),
                        "area": area,
                        "average_depth": avg_depth,
                        "centroid": (int(centroids[label][0]), int(centroids[label][1]))
                    })
        
        return foreground_objects
    
    def _extract_background_regions(self, depth_maps: List[DepthMap]) -> List[Dict[str, Any]]:
        """Extract background regions based on depth"""
        if not depth_maps:
            return []
        
        background_regions = []
        
        for i, depth_map in enumerate(depth_maps):
            # Find regions with high depth values (farther from camera)
            background_threshold = 0.7  # Objects farther than 70% of max depth
            background_mask = depth_map.depth_array > background_threshold
            
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                background_mask.astype(np.uint8), connectivity=8
            )
            
            # Extract region information
            for label in range(1, num_labels):  # Skip background (label 0)
                area = stats[label, cv2.CC_STAT_AREA]
                
                if area > 500:  # Minimum background region size
                    x, y, w, h = stats[label, cv2.CC_STAT_LEFT], stats[label, cv2.CC_STAT_TOP], \
                                stats[label, cv2.CC_STAT_WIDTH], stats[label, cv2.CC_STAT_HEIGHT]
                    
                    # Calculate average depth for this region
                    region_mask = labels == label
                    avg_depth = np.mean(depth_map.depth_array[region_mask])
                    
                    background_regions.append({
                        "frame_idx": i,
                        "bbox": (x, y, w, h),
                        "area": area,
                        "average_depth": avg_depth,
                        "centroid": (int(centroids[label][0]), int(centroids[label][1]))
                    })
        
        return background_regions
    
    def _create_depth_visualization(self, depth_map: DepthMap) -> np.ndarray:
        """Create colored depth visualization"""
        try:
            # Convert depth to 0-255 range
            depth_vis = (depth_map.depth_array * 255).astype(np.uint8)
            
            # Apply colormap for better visualization
            depth_colored = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)
            
            return depth_colored
            
        except Exception as e:
            logger.error(f"Error creating depth visualization: {e}")
            return None
    
    def get_depth_summary(self, result: DepthAnalysisResult) -> Dict[str, Any]:
        """Get summary of depth analysis results"""
        return {
            "total_depth_maps": len(result.depth_maps),
            "scene_summary": result.scene_depth_summary,
            "foreground_objects": len(result.foreground_objects),
            "background_regions": len(result.background_regions),
            "has_visualization": result.depth_visualization is not None,
            "average_confidence": np.mean([dm.confidence for dm in result.depth_maps]) if result.depth_maps else 0.0
        }
    
    def segment_by_depth(self, 
                        frame: np.ndarray, 
                        depth_map: DepthMap,
                        num_segments: int = 3) -> List[Dict[str, Any]]:
        """Segment frame into depth layers"""
        try:
            # Create depth segments
            segment_thresholds = np.linspace(0, 1, num_segments + 1)
            segments = []
            
            for i in range(num_segments):
                lower_thresh = segment_thresholds[i]
                upper_thresh = segment_thresholds[i + 1]
                
                # Create mask for this depth segment
                mask = (depth_map.depth_array >= lower_thresh) & (depth_map.depth_array < upper_thresh)
                
                # Apply mask to frame
                segmented_frame = frame.copy()
                segmented_frame[~mask] = 0
                
                # Calculate segment statistics
                segment_area = np.sum(mask)
                avg_depth = np.mean(depth_map.depth_array[mask]) if segment_area > 0 else 0.0
                
                segments.append({
                    "segment_id": i,
                    "depth_range": (lower_thresh, upper_thresh),
                    "mask": mask,
                    "area": segment_area,
                    "average_depth": avg_depth,
                    "segmented_frame": segmented_frame
                })
            
            return segments
            
        except Exception as e:
            logger.error(f"Error segmenting by depth: {e}")
            return []
    
    def calculate_object_distance(self, 
                                depth_map: DepthMap, 
                                bbox: Tuple[int, int, int, int]) -> float:
        """Calculate average distance of objects in bounding box"""
        try:
            x1, y1, x2, y2 = bbox
            
            # Ensure bbox is within image bounds
            h, w = depth_map.depth_array.shape
            x1 = max(0, min(x1, w-1))
            y1 = max(0, min(y1, h-1))
            x2 = max(0, min(x2, w-1))
            y2 = max(0, min(y2, h-1))
            
            # Extract depth values in bounding box
            depth_region = depth_map.depth_array[y1:y2, x1:x2]
            
            # Calculate average depth
            avg_depth = np.mean(depth_region)
            
            # Convert normalized depth to relative distance
            # This is a rough approximation - in practice you'd need camera calibration
            relative_distance = 1.0 / (avg_depth + 0.1)  # Avoid division by zero
            
            return relative_distance
            
        except Exception as e:
            logger.error(f"Error calculating object distance: {e}")
            return 0.0
    
    def cleanup(self):
        """Cleanup depth model resources"""
        if self.depth_model:
            del self.depth_model
            self.depth_model = None
        
        if self.processor:
            del self.processor
            self.processor = None
        
        # Clear GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Depth model cleaned up")
