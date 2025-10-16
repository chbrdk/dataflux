"""
Enhanced Video Analyzer with Scene-Based Pipeline
Main analyzer that orchestrates scene detection, extraction, and analysis
"""

import cv2
import numpy as np
import logging
import asyncio
import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from .base import BaseAnalyzer, Segment, AnalysisResult
from .scene_detector_v2 import EnhancedSceneDetector, SceneSegment
from .scene_extractor import SceneExtractor, ExtractedScene
from .scene_analyzer import SceneAnalyzer, SceneAnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class VideoAnalysisPipeline:
    """Configuration for video analysis pipeline"""
    scene_detection: Dict[str, Any]
    scene_extraction: Dict[str, Any]
    scene_analysis: Dict[str, Any]
    cleanup_temp_files: bool = True
    max_concurrent_scenes: int = 3

class EnhancedVideoAnalyzerV2(BaseAnalyzer):
    """Enhanced video analyzer with scene-based pipeline"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        
        # Initialize pipeline components
        self.scene_detector = EnhancedSceneDetector(self.config.get('scene_detection', {}))
        self.scene_extractor = SceneExtractor(self.config.get('scene_extraction', {}))
        self.scene_analyzer = SceneAnalyzer(self.config.get('scene_analysis', {}))
        
        logger.info("🎬 Enhanced Video Analyzer V2 initialized with scene-based pipeline")
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main analysis method using scene-based pipeline
        
        Args:
            file_path: Path to video file
            asset_data: Asset metadata
            
        Returns:
            Analysis results dictionary
        """
        start_time = time.time()
        self.log_analysis_start(file_path, asset_data)
        
        try:
            if not self.validate_file(file_path):
                return self.create_error_result("Invalid video file")
            
            logger.info(f"🎬 Starting scene-based analysis for: {Path(file_path).name}")
            
            # Step 1: Detect scenes
            logger.info("🔍 Step 1: Detecting scenes...")
            scenes = self.scene_detector.detect_scenes(file_path)
            logger.info(f"✅ Detected {len(scenes)} scenes")
            
            if not scenes:
                return self.create_error_result("No scenes detected")
            
            # Step 2: Extract scenes as temporary videos
            logger.info("📹 Step 2: Extracting scenes...")
            extracted_scenes = self.scene_extractor.extract_scenes(file_path, scenes)
            logger.info(f"✅ Extracted {len(extracted_scenes)} scenes")
            
            if not extracted_scenes:
                return self.create_error_result("Failed to extract scenes")
            
            # Step 3: Analyze individual scenes
            logger.info("🔍 Step 3: Analyzing scenes...")
            scene_results = await self._analyze_scenes_parallel(extracted_scenes)
            logger.info(f"✅ Analyzed {len(scene_results)} scenes")
            
            # Step 4: Aggregate results
            logger.info("📊 Step 4: Aggregating results...")
            aggregated_result = self._aggregate_results(scenes, extracted_scenes, scene_results)
            
            # Step 5: Cleanup temporary files
            if self.config.get('cleanup_temp_files', True):
                logger.info("🗑️ Step 5: Cleaning up temporary files...")
                self.scene_extractor.cleanup_all_scenes(extracted_scenes)
            
            processing_time = time.time() - start_time
            aggregated_result['metadata']['processing_time'] = processing_time
            
            self.log_analysis_end(file_path, aggregated_result)
            
            logger.info(f"🎉 Scene-based analysis completed in {processing_time:.2f}s")
            return aggregated_result
            
        except Exception as e:
            logger.error(f"❌ Scene-based analysis failed: {e}")
            return self.create_error_result(str(e))
    
    async def _analyze_scenes_parallel(self, extracted_scenes: List[ExtractedScene]) -> List[SceneAnalysisResult]:
        """Analyze scenes in parallel"""
        max_concurrent = self.config.get('max_concurrent_scenes', 3)
        
        # Create semaphore to limit concurrent analysis
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(scene):
            async with semaphore:
                return await self.scene_analyzer.analyze_scene(scene)
        
        # Run analysis in parallel
        tasks = [analyze_with_semaphore(scene) for scene in extracted_scenes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Scene analysis failed for scene {i}: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    def _aggregate_results(self, scenes: List[SceneSegment], 
                          extracted_scenes: List[ExtractedScene],
                          scene_results: List[SceneAnalysisResult]) -> Dict[str, Any]:
        """Aggregate results from all scenes"""
        
        # Create segment dictionaries for database storage
        segment_dicts = []
        all_features = []
        all_embeddings = {}
        
        for i, (scene, extracted_scene, scene_result) in enumerate(zip(scenes, extracted_scenes, scene_results)):
            # Create segment dict
            segment_dict = {
                'segment_id': scene.scene_id,
                'type': 'scene',
                'sequence_number': i,
                'start_marker': {'time': scene.start_time},
                'end_marker': {'time': scene.end_time},
                'duration': scene.duration,
                'confidence': scene_result.confidence,
                'features': scene_result.features,
                'metadata': {
                    **scene.metadata,
                    'extraction_info': self.scene_extractor.get_scene_info(extracted_scene),
                    'analysis_info': scene_result.metadata
                }
            }
            segment_dicts.append(segment_dict)
            
            # Collect features
            all_features.extend(scene_result.features)
            
            # Collect embeddings
            all_embeddings.update(scene_result.embeddings)
        
        # Add overall video features
        overall_features = self._create_overall_features(scenes, extracted_scenes, scene_results)
        all_features.extend(overall_features)
        
        # Create result
        result = self.create_success_result(
            segments=segment_dicts,
            features=all_features,
            embeddings=all_embeddings,
            metadata={
                'total_scenes': len(scenes),
                'total_features': len(all_features),
                'total_embeddings': len(all_embeddings),
                'pipeline_version': 'v2_scene_based',
                'scene_detection_method': self.scene_detector.config['method'],
                'scene_extraction_resolution': self.scene_extractor.config['output_resolution'],
                'scene_analysis_analyzers': list(self.scene_analyzer.analyzers.keys())
            }
        )
        
        return result
    
    def _create_overall_features(self, scenes: List[SceneSegment], 
                                extracted_scenes: List[ExtractedScene],
                                scene_results: List[SceneAnalysisResult]) -> List[Dict[str, Any]]:
        """Create overall video features"""
        features = []
        
        try:
            # Video structure analysis
            structure_feature = {
                'type': 'video_structure',
                'domain': 'structure',
                'confidence': 1.0,
                'data': {
                    'total_scenes': len(scenes),
                    'average_scene_duration': sum(s.duration for s in scenes) / len(scenes),
                    'shortest_scene': min(s.duration for s in scenes),
                    'longest_scene': max(s.duration for s in scenes),
                    'scene_duration_variance': np.var([s.duration for s in scenes]),
                    'total_duration': sum(s.duration for s in scenes)
                },
                'metadata': {
                    'analyzer': 'enhanced_video_analyzer_v2',
                    'pipeline': 'scene_based'
                }
            }
            features.append(structure_feature)
            
            # Scene quality analysis
            if scene_results:
                avg_confidence = sum(r.confidence for r in scene_results) / len(scene_results)
                quality_feature = {
                    'type': 'video_quality',
                    'domain': 'quality',
                    'confidence': avg_confidence,
                    'data': {
                        'average_scene_confidence': avg_confidence,
                        'high_confidence_scenes': sum(1 for r in scene_results if r.confidence > 0.8),
                        'low_confidence_scenes': sum(1 for r in scene_results if r.confidence < 0.5),
                        'total_features': sum(len(r.features) for r in scene_results),
                        'total_embeddings': sum(len(r.embeddings) for r in scene_results)
                    },
                    'metadata': {
                        'analyzer': 'enhanced_video_analyzer_v2',
                        'pipeline': 'scene_based'
                    }
                }
                features.append(quality_feature)
            
            # Scene extraction analysis
            if extracted_scenes:
                total_size = sum(s.file_size for s in extracted_scenes)
                extraction_feature = {
                    'type': 'scene_extraction',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': {
                        'total_extracted_size_mb': total_size / (1024 * 1024),
                        'average_scene_size_mb': (total_size / len(extracted_scenes)) / (1024 * 1024),
                        'extraction_resolution': extracted_scenes[0].resolution,
                        'extraction_fps': extracted_scenes[0].fps,
                        'compression_ratio': sum(s.metadata.get('compression_ratio', 0) for s in extracted_scenes) / len(extracted_scenes)
                    },
                    'metadata': {
                        'analyzer': 'enhanced_video_analyzer_v2',
                        'pipeline': 'scene_based'
                    }
                }
                features.append(extraction_feature)
            
        except Exception as e:
            logger.error(f"❌ Failed to create overall features: {e}")
        
        return features
    
    def validate_file(self, file_path: str) -> bool:
        """Validate video file"""
        try:
            if not os.path.exists(file_path):
                return False
            
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return False
            
            ret, frame = cap.read()
            cap.release()
            
            return ret and frame is not None
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False
    
    def create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'status': 'error',
            'error': error_message,
            'segments': [],
            'features': [],
            'embeddings': {},
            'metadata': {
                'analyzer': 'enhanced_video_analyzer_v2',
                'error': error_message,
                'timestamp': time.time(),
                'pipeline': 'scene_based'
            }
        }
    
    def create_success_result(self, segments: List[Dict[str, Any]], 
                            features: List[Dict[str, Any]], 
                            embeddings: Dict[str, Any], 
                            metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create success result"""
        return {
            'status': 'success',
            'segments': segments,
            'features': features,
            'embeddings': embeddings,
            'metadata': {
                **metadata,
                'analyzer': 'enhanced_video_analyzer_v2',
                'timestamp': time.time(),
                'pipeline': 'scene_based'
            }
        }
    
    def log_analysis_start(self, file_path: str, asset_data: Dict[str, Any]):
        """Log analysis start"""
        logger.info(f"🎬 Starting scene-based video analysis: {os.path.basename(file_path)}")
    
    def log_analysis_end(self, file_path: str, result: Dict[str, Any]):
        """Log analysis end"""
        status = result.get('status', 'unknown')
        logger.info(f"✅ Scene-based video analysis completed: {os.path.basename(file_path)} - Status: {status}")
    
    # BaseAnalyzer interface methods
    def extract_segments(self, file_path: str) -> List[Segment]:
        """Extract segments using scene detection"""
        scenes = self.scene_detector.detect_scenes(file_path)
        return [Segment(
            segment_id=scene.scene_id,
            start_time=scene.start_time,
            end_time=scene.end_time,
            duration=scene.duration,
            metadata=scene.metadata
        ) for scene in scenes]
    
    async def analyze_segment(self, segment: Segment) -> AnalysisResult:
        """Analyze a segment (not used in scene-based pipeline)"""
        return AnalysisResult(
            segment_id=segment.segment_id,
            analyzer_type='enhanced_video_analyzer_v2',
            confidence=0.0,
            features=[],
            embeddings={},
            metadata={}
        )
    
    def generate_embeddings(self, segment: Segment) -> Dict[str, np.ndarray]:
        """Generate embeddings for segment"""
        return {}
    
    def get_memory_requirements(self) -> Dict[str, int]:
        """Get memory requirements"""
        return {
            'scene_detector': 50 * 1024 * 1024,  # 50MB
            'scene_extractor': 100 * 1024 * 1024,  # 100MB
            'scene_analyzer': 200 * 1024 * 1024,  # 200MB
            'total': 350 * 1024 * 1024  # 350MB
        }
    
    def get_supported_formats(self) -> List[str]:
        """Get supported video formats"""
        return ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']

# Factory function
def create_enhanced_video_analyzer_v2(config: Dict[str, Any] = None) -> EnhancedVideoAnalyzerV2:
    """Create an enhanced video analyzer V2 instance"""
    return EnhancedVideoAnalyzerV2(config)
