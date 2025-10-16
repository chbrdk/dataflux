"""
Hierarchical Result Builder
Structures video analysis results in hierarchical format for database storage
"""

import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import numpy as np

from .video_config import get_video_config

logger = logging.getLogger(__name__)

class VideoAnalysisResult:
    """Container for complete video analysis results"""
    
    def __init__(self,
                 video_metadata: Dict[str, Any],
                 scenes: List[Dict[str, Any]],
                 frame_analyses: List[Dict[str, Any]],
                 audio_analysis: Optional[Dict[str, Any]] = None,
                 temporal_analysis: Optional[Dict[str, Any]] = None,
                 overall_features: List[Dict[str, Any]] = None,
                 overall_embeddings: List[Dict[str, Any]] = None):
        self.video_metadata = video_metadata
        self.scenes = scenes
        self.frame_analyses = frame_analyses
        self.audio_analysis = audio_analysis
        self.temporal_analysis = temporal_analysis
        self.overall_features = overall_features or []
        self.overall_embeddings = overall_embeddings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with hierarchical structure"""
        return {
            'video_metadata': self.video_metadata,
            'scenes': self.scenes,  # Each scene contains its features hierarchically
            'frame_analyses': self.frame_analyses,
            'audio_analysis': self.audio_analysis,
            'temporal_analysis': self.temporal_analysis,
            'overall_features': self.overall_features,
            'overall_embeddings': self.overall_embeddings,
            'structure_info': {
                'description': 'Hierarchical structure: features -> scenes -> frame_features',
                'scene_features_location': 'scenes[].features.frame_features',
                'scene_summary_location': 'scenes[].features.scene_summary',
                'features_by_type_location': 'scenes[].features.features_by_type'
            }
        }

class HierarchicalResultBuilder:
    """Builds hierarchical video analysis results for database storage"""
    
    def __init__(self):
        self.config = get_video_config()
    
    def build_video_result(self,
                          video_path: str,
                          video_info: Dict[str, Any],
                          scene_detection_result: Dict[str, Any],
                          frame_analyses: List[Dict[str, Any]],
                          audio_analysis: Optional[Dict[str, Any]] = None,
                          temporal_analysis: Optional[Dict[str, Any]] = None,
                          # Enhanced analysis results
                          object_tracking_result: Optional[Dict[str, Any]] = None,
                          action_recognition_result: Optional[Dict[str, Any]] = None,
                          pose_estimation_result: Optional[Dict[str, Any]] = None,
                          depth_estimation_result: Optional[Dict[str, Any]] = None,
                          quality_assessment_result: Optional[Dict[str, Any]] = None,
                          safety_analysis_result: Optional[Dict[str, Any]] = None) -> VideoAnalysisResult:
        """Build complete hierarchical video analysis result"""
        
        # Build video metadata
        video_metadata = self._build_video_metadata(video_path, video_info, scene_detection_result)
        
        # Build scene segments
        scenes = self._build_scene_segments(scene_detection_result, frame_analyses)
        
        # Build frame analyses with proper hierarchy
        structured_frame_analyses = self._build_frame_analyses(frame_analyses, scenes)
        
        # Build overall video features
        overall_features = self._build_overall_features(
            video_info, scene_detection_result, audio_analysis, temporal_analysis,
            object_tracking_result, action_recognition_result, pose_estimation_result,
            depth_estimation_result, quality_assessment_result, safety_analysis_result
        )
        
        # Build overall video embeddings
        overall_embeddings = self._build_overall_embeddings(frame_analyses)
        
        return VideoAnalysisResult(
            video_metadata=video_metadata,
            scenes=scenes,
            frame_analyses=structured_frame_analyses,
            audio_analysis=audio_analysis,
            temporal_analysis=temporal_analysis,
            overall_features=overall_features,
            overall_embeddings=overall_embeddings
        )
    
    def _build_video_metadata(self, 
                             video_path: str, 
                             video_info: Dict[str, Any],
                             scene_detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build video-level metadata"""
        return {
            'video_path': video_path,
            'duration': video_info.get('duration', 0),
            'fps': video_info.get('fps', 0),
            'width': video_info.get('width', 0),
            'height': video_info.get('height', 0),
            'frame_count': video_info.get('frame_count', 0),
            'codec': video_info.get('codec', 'unknown'),
            'total_scenes': len(scene_detection_result.get('scenes', [])),
            'scene_detection_method': scene_detection_result.get('detection_method', 'unknown'),
            'scene_detection_confidence': scene_detection_result.get('confidence', 0.0),
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'config_used': self.config.to_dict()
        }
    
    def _build_scene_segments(self, 
                             scene_detection_result: Dict[str, Any],
                             frame_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build scene segments with hierarchical features structure"""
        scenes = []
        detected_scenes = scene_detection_result.get('scenes', [])
        
        for scene in detected_scenes:
            scene_id = scene['scene_id']
            
            # Find frames belonging to this scene
            scene_frames = [f for f in frame_analyses if f.get('scene_id') == scene_id]
            
            # Collect all features from frames in this scene (hierarchical structure)
            scene_features = self._collect_scene_features(scene_frames)
            
            # Build scene segment with hierarchical features
            scene_segment = {
                'segment_id': str(uuid.uuid4()),
                'segment_type': 'scene',
                'sequence_number': scene_id,
                'start_marker': {'time': scene['start_time']},
                'end_marker': {'time': scene['end_time']},
                'duration': scene['duration'],
                'confidence_score': scene.get('confidence', 0.8),
                'frame_count': len(scene_frames),
                'features': scene_features,  # Hierarchical features structure
                'metadata': {
                    'scene_id': scene_id,
                    'detection_method': scene.get('detection_method', 'unknown'),
                    'start_frame': scene.get('start_frame', 0),
                    'end_frame': scene.get('end_frame', 0)
                }
            }
            
            scenes.append(scene_segment)
        
        return scenes
    
    def _build_frame_analyses(self, 
                             frame_analyses: List[Dict[str, Any]],
                             scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build structured frame analyses with proper hierarchy"""
        structured_frames = []
        
        for frame_analysis in frame_analyses:
            scene_id = frame_analysis.get('scene_id', 0)
            timestamp = frame_analysis.get('timestamp', 0)
            
            # Find parent scene
            parent_scene = None
            for scene in scenes:
                if scene['metadata']['scene_id'] == scene_id:
                    parent_scene = scene
                    break
            
            # Build frame segment
            frame_segment = {
                'segment_id': str(uuid.uuid4()),
                'segment_type': 'frame',
                'parent_id': parent_scene['segment_id'] if parent_scene else None,
                'sequence_number': frame_analysis.get('frame_index', 0),
                'start_marker': {'time': timestamp},
                'end_marker': {'time': timestamp + 0.1},  # Short duration for frame
                'duration': 0.1,
                'confidence_score': frame_analysis.get('confidence', 0.9),
                'features': frame_analysis.get('features', []),
                'embeddings': frame_analysis.get('embeddings', []),
                'metadata': {
                    'frame_id': frame_analysis.get('frame_id'),
                    'scene_id': scene_id,
                    'timestamp': timestamp,
                    'frame_index': frame_analysis.get('frame_index', 0),
                    'image_path': frame_analysis.get('image_path'),
                    'thumbnail_path': frame_analysis.get('thumbnail_path'),
                    'is_keyframe': frame_analysis.get('is_keyframe', False),
                    'is_scene_boundary': frame_analysis.get('is_scene_boundary', False)
                }
            }
            
            structured_frames.append(frame_segment)
        
        return structured_frames
    
    def _collect_scene_features(self, scene_frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect features from frames in a scene and organize them hierarchically
        Structure: features -> scenes -> frame_features
        """
        if not scene_frames:
            return {
                'frame_features': [],
                'scene_summary': {
                    'total_frames': 0,
                    'feature_types': [],
                    'confidence_avg': 0.0
                }
            }
        
        # Collect all features from frames with frame context
        frame_features = []
        feature_types = set()
        confidence_scores = []
        
        for frame_idx, frame in enumerate(scene_frames):
            frame_timestamp = frame.get('timestamp', 0)
            frame_features_list = frame.get('features', [])
            
            # Add frame context to each feature
            for feature in frame_features_list:
                enhanced_feature = {
                    **feature,  # Keep original feature data
                    'frame_context': {
                        'frame_index': frame_idx,
                        'timestamp': frame_timestamp,
                        'is_keyframe': frame.get('is_keyframe', False),
                        'is_scene_boundary': frame.get('is_scene_boundary', False)
                    }
                }
                frame_features.append(enhanced_feature)
                
                # Track feature types and confidence
                feature_types.add(feature.get('type', 'unknown'))
                confidence_scores.append(feature.get('confidence', 0.5))
        
        # Create scene summary
        scene_summary = {
            'total_frames': len(scene_frames),
            'total_features': len(frame_features),
            'feature_types': list(feature_types),
            'confidence_avg': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            'confidence_min': min(confidence_scores) if confidence_scores else 0.0,
            'confidence_max': max(confidence_scores) if confidence_scores else 0.0
        }
        
        # Group features by type for better organization
        features_by_type = {}
        for feature in frame_features:
            feature_type = feature.get('type', 'unknown')
            if feature_type not in features_by_type:
                features_by_type[feature_type] = []
            features_by_type[feature_type].append(feature)
        
        return {
            'frame_features': frame_features,  # All features with frame context
            'features_by_type': features_by_type,  # Features grouped by type
            'scene_summary': scene_summary
        }
    
    def _build_overall_features(self,
                               video_info: Dict[str, Any],
                               scene_detection_result: Dict[str, Any],
                               audio_analysis: Optional[Dict[str, Any]] = None,
                               temporal_analysis: Optional[Dict[str, Any]] = None,
                               # Enhanced analysis results
                               object_tracking_result: Optional[Dict[str, Any]] = None,
                               action_recognition_result: Optional[Dict[str, Any]] = None,
                               pose_estimation_result: Optional[Dict[str, Any]] = None,
                               depth_estimation_result: Optional[Dict[str, Any]] = None,
                               quality_assessment_result: Optional[Dict[str, Any]] = None,
                               safety_analysis_result: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Build video-level features"""
        features = []
        
        # Video technical features
        features.append({
            'type': 'video_technical',
            'domain': 'technical',
            'confidence': 1.0,
            'data': {
                'duration': video_info.get('duration', 0),
                'fps': video_info.get('fps', 0),
                'resolution': f"{video_info.get('width', 0)}x{video_info.get('height', 0)}",
                'frame_count': video_info.get('frame_count', 0),
                'codec': video_info.get('codec', 'unknown'),
                'file_size': video_info.get('file_size', 0)
            },
            'metadata': {'analyzer': 'video_technical'}
        })
        
        # Scene analysis features
        scenes = scene_detection_result.get('scenes', [])
        if scenes:
            scene_durations = [s['duration'] for s in scenes]
            features.append({
                'type': 'video_scene_analysis',
                'domain': 'visual',
                'confidence': scene_detection_result.get('confidence', 0.8),
                'data': {
                    'total_scenes': len(scenes),
                    'average_scene_length': sum(scene_durations) / len(scene_durations),
                    'shortest_scene': min(scene_durations),
                    'longest_scene': max(scene_durations),
                    'scene_length_variance': self._calculate_variance(scene_durations),
                    'detection_method': scene_detection_result.get('detection_method', 'unknown')
                },
                'metadata': {'analyzer': 'scene_analysis'}
            })
        
        # Audio features
        if audio_analysis:
            features.append({
                'type': 'video_audio_analysis',
                'domain': 'technical',
                'confidence': 0.9,
                'data': {
                    'has_audio': audio_analysis.get('has_audio', False),
                    'duration': audio_analysis.get('duration', 0),
                    'sample_rate': audio_analysis.get('sample_rate', 0),
                    'channels': audio_analysis.get('channels', 0),
                    'silence_segments': len(audio_analysis.get('silence_segments', [])),
                    'avg_volume': np.mean(audio_analysis.get('volume_levels', [])) if audio_analysis.get('volume_levels') else -60.0
                },
                'metadata': {'analyzer': 'audio_analysis'}
            })
        
        # Temporal features
        if temporal_analysis:
            features.append({
                'type': 'video_temporal_analysis',
                'domain': 'technical',
                'confidence': 0.8,
                'data': temporal_analysis,
                'metadata': {'analyzer': 'temporal_analysis'}
            })
        
        # Enhanced Features Integration
        # Object Tracking Features
        if object_tracking_result:
            features.append({
                'type': 'object_tracking',
                'domain': 'temporal',
                'confidence': object_tracking_result.get('confidence', 0.8),
                'data': object_tracking_result.get('data', {}),
                'metadata': {'analyzer': 'object_tracker'}
            })
        
        # Quality Assessment Features
        if quality_assessment_result:
            features.append({
                'type': 'quality_assessment',
                'domain': 'quality',
                'confidence': quality_assessment_result.get('confidence', 0.8),
                'data': quality_assessment_result.get('data', {}),
                'metadata': {'analyzer': 'quality_analyzer'}
            })
        
        # Safety Analysis Features
        if safety_analysis_result:
            features.append({
                'type': 'safety_analysis',
                'domain': 'safety',
                'confidence': safety_analysis_result.get('confidence', 0.8),
                'data': safety_analysis_result.get('data', {}),
                'metadata': {'analyzer': 'safety_analyzer'}
            })
        
        # Action Recognition Features
        if action_recognition_result:
            features.append({
                'type': 'action_recognition',
                'domain': 'visual',
                'confidence': action_recognition_result.get('confidence', 0.8),
                'data': action_recognition_result.get('data', {}),
                'metadata': {'analyzer': 'action_recognizer'}
            })
        
        # Pose Estimation Features (Pro-Tier)
        if pose_estimation_result:
            features.append({
                'type': 'pose_estimation',
                'domain': 'visual',
                'confidence': pose_estimation_result.get('confidence', 0.8),
                'data': pose_estimation_result.get('data', {}),
                'metadata': {'analyzer': 'pose_estimator'}
            })
        
        # Depth Estimation Features (Pro-Tier)
        if depth_estimation_result:
            features.append({
                'type': 'depth_estimation',
                'domain': 'visual',
                'confidence': depth_estimation_result.get('confidence', 0.8),
                'data': depth_estimation_result.get('data', {}),
                'metadata': {'analyzer': 'depth_estimator'}
            })
        
        return features
    
    def _build_overall_embeddings(self, frame_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build video-level embeddings from frame embeddings"""
        embeddings = []
        
        # Collect all frame embeddings
        all_embeddings = []
        for frame_analysis in frame_analyses:
            all_embeddings.extend(frame_analysis.get('embeddings', []))
        
        # Group embeddings by type
        embedding_groups = {}
        for embedding in all_embeddings:
            embedding_type = embedding.get('type', 'unknown')
            if embedding_type not in embedding_groups:
                embedding_groups[embedding_type] = []
            embedding_groups[embedding_type].append(embedding)
        
        # Create temporal embeddings
        for embedding_type, embedding_list in embedding_groups.items():
            if len(embedding_list) > 1:
                # Calculate mean embedding
                embeddings_data = [e.get('embedding', []) for e in embedding_list]
                if embeddings_data and len(embeddings_data[0]) > 0:
                    mean_embedding = np.mean(embeddings_data, axis=0).tolist()
                    
                    embeddings.append({
                        'type': f'video_temporal_{embedding_type}',
                        'model': embedding_list[0].get('model', 'unknown'),
                        'dimensions': len(mean_embedding),
                        'embedding': mean_embedding,
                        'metadata': {
                            'analyzer': 'temporal_pooling',
                            'frame_count': len(embedding_list),
                            'pooling_method': 'mean'
                        }
                    })
        
        return embeddings
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def to_database_format(self, video_result: VideoAnalysisResult, asset_id: str) -> Dict[str, Any]:
        """Convert video result to database storage format"""
        return {
            'asset_id': asset_id,
            'video_metadata': video_result.video_metadata,
            'segments': video_result.scenes + video_result.frame_analyses,
            'features': video_result.overall_features,
            'embeddings': video_result.overall_embeddings,
            'audio_analysis': video_result.audio_analysis,
            'temporal_analysis': video_result.temporal_analysis,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'total_segments': len(video_result.scenes) + len(video_result.frame_analyses),
            'total_features': len(video_result.overall_features),
            'total_embeddings': len(video_result.overall_embeddings)
        }
