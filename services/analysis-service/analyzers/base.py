"""
Base analyzer interface for DataFlux analysis service
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class Segment:
    """Base segment for analysis"""
    segment_id: str
    start_time: float
    end_time: float
    duration: float
    metadata: Dict[str, Any]


@dataclass
class AnalysisResult:
    """Base analysis result"""
    segment_id: str
    analyzer_type: str
    features: List[Dict[str, Any]]
    embeddings: Dict[str, np.ndarray]
    confidence: float
    metadata: Dict[str, Any]


class BaseAnalyzer(ABC):
    """Abstract base class for all analyzers"""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get supported MIME types"""
        pass
    
    @abstractmethod
    def extract_segments(self, file_path: str) -> List[Segment]:
        """Extract segments from file"""
        pass
    
    @abstractmethod
    def analyze_segment(self, segment: Segment) -> AnalysisResult:
        """Analyze a single segment"""
        pass
    
    @abstractmethod
    def generate_embeddings(self, segment: Segment) -> Dict[str, np.ndarray]:
        """Generate embeddings for segment"""
        pass
    
    @abstractmethod
    def get_memory_requirements(self) -> Dict[str, int]:
        """Get RAM requirements per model"""
        pass