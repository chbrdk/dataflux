"""
Base Analyzer Class for DataFlux Analysis Service
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class BaseAnalyzer(ABC):
    """Base class for all media analyzers"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.supported_formats = []
        self.model = None
        self.device = "cpu"  # Default to CPU, can be overridden
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported MIME types"""
        pass
    
    @abstractmethod
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze media file and return structured results
        
        Args:
            file_path: Path to the media file
            asset_data: Asset metadata from database
            
        Returns:
            Dict containing:
            - segments: List of detected segments
            - features: List of extracted features
            - embeddings: List of vector embeddings
            - metadata: Additional analysis metadata
        """
        pass
    
    def extract_segments(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract segments from analysis data"""
        segments = []
        
        # Override in subclasses for specific segment extraction
        return segments
    
    def extract_features(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract features from analysis data"""
        features = []
        
        # Override in subclasses for specific feature extraction
        return features
    
    def generate_embeddings(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate embeddings from analysis data"""
        embeddings = []
        
        # Override in subclasses for specific embedding generation
        return embeddings
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that the file can be processed"""
        import os
        return os.path.exists(file_path) and os.path.getsize(file_path) > 0
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic file information"""
        import os
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'exists': True
        }
    
    def log_analysis_start(self, file_path: str, asset_data: Dict[str, Any]):
        """Log analysis start"""
        logger.info(f"Starting {self.name} analysis for {file_path}")
    
    def log_analysis_end(self, file_path: str, results: Dict[str, Any]):
        """Log analysis completion"""
        logger.info(f"Completed {self.name} analysis for {file_path}: {len(results.get('segments', []))} segments, {len(results.get('features', []))} features, {len(results.get('embeddings', []))} embeddings")
    
    def create_error_result(self, error: str) -> Dict[str, Any]:
        """Create error result structure"""
        return {
            'segments': [],
            'features': [],
            'embeddings': [],
            'metadata': {
                'error': error,
                'analyzer': self.name,
                'status': 'failed'
            }
        }
    
    def create_success_result(self, segments: List[Dict], features: List[Dict], 
                            embeddings: List[Dict], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create success result structure"""
        return {
            'segments': segments,
            'features': features,
            'embeddings': embeddings,
            'metadata': {
                **metadata,
                'analyzer': self.name,
                'status': 'success'
            }
        }
