"""
GPT-5 Vision Configuration für Video Analyzer
"""

import os
from enum import Enum
from typing import Optional

class GPT5VisionMode(Enum):
    """GPT-5 Vision analysis modes"""
    DISABLED = "disabled"
    KEYFRAMES_ONLY = "keyframes_only"
    ALL_FRAMES = "all_frames"
    SMART_SAMPLING = "smart_sampling"
    NANO_ONLY = "nano_only"  # Nur GPT-5-nano verwenden

class GPT5VisionConfig:
    """Configuration für GPT-5 Vision Integration"""
    
    def __init__(self):
        # GPT-5 Vision settings
        self.gpt5_vision_mode: GPT5VisionMode = GPT5VisionMode.NANO_ONLY  # Default zu nano
        self.gpt5_rate_limit: int = 30  # GPT-5 hat höhere Limits
        self.gpt5_max_tokens: int = 3000  # GPT-5 kann mehr Tokens
        self.gpt5_temperature: float = 0.2  # GPT-5 ist präziser
        self.gpt5_detail_level: str = "high"  # GPT-5 unterstützt höhere Details
        
        # Bildvorverarbeitung (GPT-5 kann größere Bilder)
        self.max_image_dimension: int = 4096  # GPT-5 kann größere Bilder
        self.image_quality: int = 90  # Höhere Qualität für GPT-5
        self.max_image_size_mb: int = 50  # GPT-5 unterstützt größere Dateien
        
        # Frame-Sampling
        self.frames_per_segment: int = 8  # Mehr Frames für GPT-5
        self.keyframe_threshold: float = 0.8  # Höhere Schwelle für GPT-5
        
        # Kosten-Optimierung
        self.enable_cost_tracking: bool = True
        self.max_cost_per_video: float = 2.0  # GPT-5 ist teurer
        self.prefer_nano_for_simple: bool = True  # Nano für einfache Bilder
        
        # GPT-5 spezifische Features
        self.enable_reasoning_mode: bool = True  # GPT-5's erweiterte Reasoning
        self.enable_cultural_analysis: bool = True  # Kulturelle Kontextanalyse
        self.enable_emotional_intelligence: bool = True  # Emotionale Intelligenz
        
        # Load from environment
        self._load_from_env()
    
    def _load_from_env(self):
        """Lade Konfiguration aus Umgebungsvariablen"""
        try:
            self.gpt5_vision_mode = GPT5VisionMode(
                os.getenv('GPT5_VISION_MODE', 'nano_only')
            )
        except ValueError:
            self.gpt5_vision_mode = GPT5VisionMode.NANO_ONLY
        
        self.gpt5_rate_limit = int(os.getenv('GPT5_RATE_LIMIT', '30'))
        self.gpt5_max_tokens = int(os.getenv('GPT5_MAX_TOKENS', '3000'))
        self.gpt5_temperature = float(os.getenv('GPT5_TEMPERATURE', '0.2'))
        self.gpt5_detail_level = os.getenv('GPT5_DETAIL_LEVEL', 'high')
        
        self.max_image_dimension = int(os.getenv('MAX_IMAGE_DIMENSION', '4096'))
        self.image_quality = int(os.getenv('IMAGE_QUALITY', '90'))
        self.max_image_size_mb = int(os.getenv('MAX_IMAGE_SIZE_MB', '50'))
        
        self.frames_per_segment = int(os.getenv('FRAMES_PER_SEGMENT', '8'))
        self.keyframe_threshold = float(os.getenv('KEYFRAME_THRESHOLD', '0.8'))
        
        self.enable_cost_tracking = os.getenv('ENABLE_COST_TRACKING', 'true').lower() == 'true'
        self.max_cost_per_video = float(os.getenv('MAX_COST_PER_VIDEO', '2.0'))
        self.prefer_nano_for_simple = os.getenv('PREFER_NANO_FOR_SIMPLE', 'true').lower() == 'true'
        
        self.enable_reasoning_mode = os.getenv('ENABLE_REASONING_MODE', 'true').lower() == 'true'
        self.enable_cultural_analysis = os.getenv('ENABLE_CULTURAL_ANALYSIS', 'true').lower() == 'true'
        self.enable_emotional_intelligence = os.getenv('ENABLE_EMOTIONAL_INTELLIGENCE', 'true').lower() == 'true'
    
    def should_use_gpt5(self, frame_context: Optional[dict] = None) -> bool:
        """Bestimmt ob GPT-5 für diesen Frame verwendet werden soll"""
        if self.gpt5_vision_mode == GPT5VisionMode.DISABLED:
            return False
        elif self.gpt5_vision_mode == GPT5VisionMode.ALL_FRAMES:
            return True
        elif self.gpt5_vision_mode == GPT5VisionMode.KEYFRAMES_ONLY:
            # Verwende GPT-5 nur für Schlüsselbilder
            if frame_context and 'is_keyframe' in frame_context:
                return frame_context['is_keyframe']
            return True  # Default für unbekannte Frames
        elif self.gpt5_vision_mode == GPT5VisionMode.SMART_SAMPLING:
            # Intelligente Auswahl basierend auf Frame-Komplexität
            if frame_context and 'complexity_score' in frame_context:
                return frame_context['complexity_score'] > self.keyframe_threshold
            return True  # Default für unbekannte Frames
        elif self.gpt5_vision_mode == GPT5VisionMode.NANO_ONLY:
            # Verwende nur GPT-5-nano für alle Frames
            return True
        
        return False
    
    def should_use_nano(self, frame_context: Optional[dict] = None) -> bool:
        """Bestimmt ob GPT-5-nano statt GPT-5 verwendet werden soll"""
        if self.gpt5_vision_mode == GPT5VisionMode.NANO_ONLY:
            return True
        
        if self.prefer_nano_for_simple and frame_context:
            # Verwende nano für einfache Bilder
            complexity = frame_context.get('complexity_score', 0.5)
            return complexity < 0.6
        
        return False
    
    def get_cost_estimate(self, num_frames: int, use_nano: bool = True) -> float:
        """Schätzt die Kosten für GPT-5 Vision Analyse"""
        # GPT-5 Vision Kosten (Stand Dezember 2024):
        # GPT-5: Input: $0.005 per 1K tokens, Output: $0.015 per 1K tokens
        # GPT-5-nano: Input: $0.002 per 1K tokens, Output: $0.008 per 1K tokens
        
        if use_nano:
            tokens_per_frame = 600  # nano ist effizienter
            cost_per_1k = 0.002 + 0.008  # Input + Output
        else:
            tokens_per_frame = 800  # GPT-5 ist detaillierter
            cost_per_1k = 0.005 + 0.015  # Input + Output
        
        total_tokens = num_frames * tokens_per_frame
        estimated_cost = (total_tokens / 1000) * cost_per_1k
        
        return estimated_cost
    
    def to_dict(self) -> dict:
        """Konvertiert Konfiguration zu Dictionary"""
        return {
            'gpt5_vision_mode': self.gpt5_vision_mode.value,
            'gpt5_rate_limit': self.gpt5_rate_limit,
            'gpt5_max_tokens': self.gpt5_max_tokens,
            'gpt5_temperature': self.gpt5_temperature,
            'gpt5_detail_level': self.gpt5_detail_level,
            'max_image_dimension': self.max_image_dimension,
            'image_quality': self.image_quality,
            'max_image_size_mb': self.max_image_size_mb,
            'frames_per_segment': self.frames_per_segment,
            'keyframe_threshold': self.keyframe_threshold,
            'enable_cost_tracking': self.enable_cost_tracking,
            'max_cost_per_video': self.max_cost_per_video,
            'prefer_nano_for_simple': self.prefer_nano_for_simple,
            'enable_reasoning_mode': self.enable_reasoning_mode,
            'enable_cultural_analysis': self.enable_cultural_analysis,
            'enable_emotional_intelligence': self.enable_emotional_intelligence
        }

# Globale Konfiguration
gpt5_config = GPT5VisionConfig()

def get_gpt5_config() -> GPT5VisionConfig:
    """Holt die globale GPT-5 Konfiguration"""
    return gpt5_config
