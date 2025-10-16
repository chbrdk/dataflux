#!/usr/bin/env python3
"""
Configuration Management für Enhanced Video Analysis Pipeline
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Tier Configurations
TIER_CONFIGS = {
    "lite": {
        "max_ram_gb": 16,
        "models": ["whisper_small", "yolo_nano", "clip_base"],
        "features": ["basic"],
        "max_concurrent_jobs": 1,
        "enable_advanced_features": False
    },
    "standard": {
        "max_ram_gb": 24,
        "models": ["whisper_medium", "yolo_medium", "clip_large", "facenet"],
        "features": ["basic", "faces", "ocr", "action_recognition"],
        "max_concurrent_jobs": 2,
        "enable_advanced_features": False
    },
    "pro": {
        "max_ram_gb": 48,
        "models": ["whisper_large", "yolo_large", "clip_large", "facenet", "mediapipe", "depth"],
        "features": ["all"],
        "max_concurrent_jobs": 4,
        "enable_advanced_features": True
    }
}

class VideoAnalysisConfig(BaseModel):
    """Configuration for video analysis features"""
    enable_scene_detection: bool = True
    enable_object_detection: bool = True
    enable_face_recognition: bool = True
    enable_ocr: bool = True
    enable_action_recognition: bool = False
    enable_pose_estimation: bool = False
    enable_depth_estimation: bool = False
    enable_nsfw_detection: bool = False
    enable_quality_assessment: bool = True
    enable_video_summarization: bool = False
    
    # Frame sampling
    frame_sampling_rate: int = Field(default=2, ge=1, le=10)  # seconds between frames
    max_frames_per_scene: int = Field(default=50, ge=1, le=200)
    
    # Claude Vision settings
    claude_vision_mode: str = Field(default="keyframes_only")  # all_frames, keyframes_only, disabled
    claude_api_key: Optional[str] = None
    
    # Processing settings
    batch_size: int = Field(default=5, ge=1, le=20)
    parallel_processing: bool = True
    max_processing_time_minutes: int = Field(default=30, ge=1, le=120)

class ModelConfig(BaseModel):
    """Configuration for model management"""
    tier: str = Field(default="auto")  # auto, lite, standard, pro
    model_cache_dir: str = "/tmp/dataflux_models"
    use_coreml: bool = True
    auto_unload_threshold: float = Field(default=0.8, ge=0.5, le=0.95)
    max_models_in_memory: int = Field(default=5, ge=1, le=20)

class DatabaseConfig(BaseModel):
    """Configuration for database connections"""
    database_url: str
    redis_url: str = "redis://localhost:6379"
    weaviate_url: str = "http://localhost:8080"
    max_connections: int = Field(default=10, ge=1, le=100)
    connection_timeout: int = Field(default=30, ge=1, le=300)

class LLMConfig(BaseModel):
    """Configuration for LLM services"""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    use_local_llm: bool = False
    local_llm_model: Optional[str] = None
    max_tokens: int = Field(default=4000, ge=100, le=32000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class MonitoringConfig(BaseModel):
    """Configuration for monitoring and logging"""
    enable_metrics: bool = True
    log_level: str = Field(default="INFO")
    structured_logging: bool = True
    sentry_dsn: Optional[str] = None
    prometheus_port: int = Field(default=9090, ge=1000, le=65535)

class Settings(BaseSettings):
    """Main settings class"""
    
    # General
    environment: str = Field(default="development")
    debug: bool = False
    
    # Service URLs
    ingestion_service_url: str = "http://localhost:2013"
    analysis_service_url: str = "http://localhost:2014"
    query_service_url: str = "http://localhost:2015"
    
    # Storage
    storage_base_path: str = "/tmp/dataflux_storage"
    temp_dir: str = "/tmp/dataflux_temp"
    
    # Processing
    max_concurrent_jobs: int = Field(default=2, ge=1, le=10)
    max_video_size_mb: int = Field(default=500, ge=10, le=5000)
    max_processing_time_minutes: int = Field(default=30, ge=1, le=120)
    
    # Video Analysis
    video_analysis: VideoAnalysisConfig = Field(default_factory=VideoAnalysisConfig)
    
    # Model Management
    model_config: ModelConfig = Field(default_factory=ModelConfig)
    
    # Database
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(
        database_url=os.getenv("DATABASE_URL", "postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux")
    ))
    
    # LLM
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # Monitoring
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "DATAFLUX_",
        "env_nested_delimiter": "__"
    }

def get_tier_config(tier: str) -> Dict[str, Any]:
    """Get configuration for a specific tier"""
    if tier not in TIER_CONFIGS:
        logger.warning(f"Unknown tier: {tier}, falling back to 'lite'")
        tier = "lite"
    
    return TIER_CONFIGS[tier]

def detect_optimal_tier() -> str:
    """Detect optimal tier based on system resources"""
    try:
        import psutil
        
        # Get available RAM
        total_ram = psutil.virtual_memory().total / (1024**3)
        
        # Get CPU count
        cpu_count = psutil.cpu_count()
        
        # Determine tier based on resources
        if total_ram >= 48 and cpu_count >= 8:
            return "pro"
        elif total_ram >= 24 and cpu_count >= 4:
            return "standard"
        else:
            return "lite"
            
    except Exception as e:
        logger.warning(f"Failed to detect optimal tier: {e}")
        return "lite"

def validate_tier_compatibility(settings: Settings, tier: str) -> bool:
    """Validate if current system can support the requested tier"""
    try:
        import psutil
        
        tier_config = get_tier_config(tier)
        required_ram = tier_config["max_ram_gb"]
        available_ram = psutil.virtual_memory().total / (1024**3)
        
        if available_ram < required_ram:
            logger.warning(
                f"Tier {tier} requires {required_ram}GB RAM, "
                f"but only {available_ram:.1f}GB available"
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate tier compatibility: {e}")
        return False

def apply_tier_config(settings: Settings, tier: str) -> Settings:
    """Apply tier-specific configuration to settings"""
    tier_config = get_tier_config(tier)
    
    # Update model config
    settings.model_config.tier = tier
    settings.model_config.max_models_in_memory = min(
        len(tier_config["models"]), 
        settings.model_config.max_models_in_memory
    )
    
    # Update processing config
    settings.max_concurrent_jobs = tier_config["max_concurrent_jobs"]
    
    # Update video analysis config based on tier
    if tier == "lite":
        settings.video_analysis.enable_action_recognition = False
        settings.video_analysis.enable_pose_estimation = False
        settings.video_analysis.enable_depth_estimation = False
        settings.video_analysis.claude_vision_mode = "disabled"
    elif tier == "standard":
        settings.video_analysis.enable_action_recognition = True
        settings.video_analysis.enable_pose_estimation = False
        settings.video_analysis.enable_depth_estimation = False
        settings.video_analysis.claude_vision_mode = "keyframes_only"
    elif tier == "pro":
        settings.video_analysis.enable_action_recognition = True
        settings.video_analysis.enable_pose_estimation = True
        settings.video_analysis.enable_depth_estimation = True
        settings.video_analysis.claude_vision_mode = "keyframes_only"
    
    logger.info(f"Applied tier {tier} configuration")
    return settings

def load_settings_from_env() -> Settings:
    """Load settings from environment variables"""
    try:
        settings = Settings()
        
        # Auto-detect tier if set to "auto"
        if settings.model_config.tier == "auto":
            optimal_tier = detect_optimal_tier()
            settings = apply_tier_config(settings, optimal_tier)
            logger.info(f"Auto-detected optimal tier: {optimal_tier}")
        
        # Validate tier compatibility
        if not validate_tier_compatibility(settings, settings.model_config.tier):
            logger.warning("Falling back to 'lite' tier due to insufficient resources")
            settings = apply_tier_config(settings, "lite")
        
        return settings
        
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        # Return minimal settings as fallback
        return Settings()

def get_feature_config(settings: Settings) -> Dict[str, bool]:
    """Get feature configuration based on current settings"""
    tier = settings.model_config.tier
    tier_config = get_tier_config(tier)
    
    # Base features
    features = {
        "scene_detection": True,
        "object_detection": True,
        "face_recognition": tier in ["standard", "pro"],
        "ocr": tier in ["standard", "pro"],
        "action_recognition": tier in ["standard", "pro"],
        "pose_estimation": tier == "pro",
        "depth_estimation": tier == "pro",
        "nsfw_detection": False,  # Explicitly enabled
        "quality_assessment": True,
        "video_summarization": settings.video_analysis.enable_video_summarization
    }
    
    # Override with explicit settings
    features.update({
        "scene_detection": settings.video_analysis.enable_scene_detection,
        "object_detection": settings.video_analysis.enable_object_detection,
        "face_recognition": settings.video_analysis.enable_face_recognition,
        "ocr": settings.video_analysis.enable_ocr,
        "action_recognition": settings.video_analysis.enable_action_recognition,
        "pose_estimation": settings.video_analysis.enable_pose_estimation,
        "depth_estimation": settings.video_analysis.enable_depth_estimation,
        "nsfw_detection": settings.video_analysis.enable_nsfw_detection,
        "quality_assessment": settings.video_analysis.enable_quality_assessment,
        "video_summarization": settings.video_analysis.enable_video_summarization
    })
    
    return features

def create_env_example() -> str:
    """Create example .env file content"""
    return """# DataFlux Configuration Example
# Copy this to .env and adjust values as needed

# General
DATAFLUX_ENVIRONMENT=development
DATAFLUX_DEBUG=false

# Service URLs
DATAFLUX_INGESTION_SERVICE_URL=http://localhost:2013
DATAFLUX_ANALYSIS_SERVICE_URL=http://localhost:2014
DATAFLUX_QUERY_SERVICE_URL=http://localhost:2015

# Storage
DATAFLUX_STORAGE_BASE_PATH=/tmp/dataflux_storage
DATAFLUX_TEMP_DIR=/tmp/dataflux_temp

# Processing
DATAFLUX_MAX_CONCURRENT_JOBS=2
DATAFLUX_MAX_VIDEO_SIZE_MB=500
DATAFLUX_MAX_PROCESSING_TIME_MINUTES=30

# Model Management
DATAFLUX_MODEL_CONFIG__TIER=auto
DATAFLUX_MODEL_CONFIG__MODEL_CACHE_DIR=/tmp/dataflux_models
DATAFLUX_MODEL_CONFIG__USE_COREML=true
DATAFLUX_MODEL_CONFIG__AUTO_UNLOAD_THRESHOLD=0.8
DATAFLUX_MODEL_CONFIG__MAX_MODELS_IN_MEMORY=5

# Video Analysis
DATAFLUX_VIDEO_ANALYSIS__ENABLE_SCENE_DETECTION=true
DATAFLUX_VIDEO_ANALYSIS__ENABLE_OBJECT_DETECTION=true
DATAFLUX_VIDEO_ANALYSIS__ENABLE_FACE_RECOGNITION=true
DATAFLUX_VIDEO_ANALYSIS__ENABLE_OCR=true
DATAFLUX_VIDEO_ANALYSIS__ENABLE_ACTION_RECOGNITION=false
DATAFLUX_VIDEO_ANALYSIS__ENABLE_POSE_ESTIMATION=false
DATAFLUX_VIDEO_ANALYSIS__ENABLE_DEPTH_ESTIMATION=false
DATAFLUX_VIDEO_ANALYSIS__ENABLE_NSFW_DETECTION=false
DATAFLUX_VIDEO_ANALYSIS__ENABLE_QUALITY_ASSESSMENT=true
DATAFLUX_VIDEO_ANALYSIS__ENABLE_VIDEO_SUMMARIZATION=false

DATAFLUX_VIDEO_ANALYSIS__FRAME_SAMPLING_RATE=2
DATAFLUX_VIDEO_ANALYSIS__MAX_FRAMES_PER_SCENE=50
DATAFLUX_VIDEO_ANALYSIS__CLAUDE_VISION_MODE=keyframes_only
DATAFLUX_VIDEO_ANALYSIS__BATCH_SIZE=5
DATAFLUX_VIDEO_ANALYSIS__PARALLEL_PROCESSING=true

# Database
DATAFLUX_DATABASE__DATABASE_URL=postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux
DATAFLUX_DATABASE__REDIS_URL=redis://localhost:6379
DATAFLUX_DATABASE__WEAVIATE_URL=http://localhost:8080
DATAFLUX_DATABASE__MAX_CONNECTIONS=10
DATAFLUX_DATABASE__CONNECTION_TIMEOUT=30

# LLM
DATAFLUX_LLM__OPENAI_API_KEY=your_openai_api_key_here
DATAFLUX_LLM__ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATAFLUX_LLM__USE_LOCAL_LLM=false
DATAFLUX_LLM__MAX_TOKENS=4000
DATAFLUX_LLM__TEMPERATURE=0.7

# Monitoring
DATAFLUX_MONITORING__ENABLE_METRICS=true
DATAFLUX_MONITORING__LOG_LEVEL=INFO
DATAFLUX_MONITORING__STRUCTURED_LOGGING=true
DATAFLUX_MONITORING__SENTRY_DSN=your_sentry_dsn_here
DATAFLUX_MONITORING__PROMETHEUS_PORT=9090
"""

# Global settings instance
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = load_settings_from_env()
    return _settings_instance

def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings_instance
    _settings_instance = load_settings_from_env()
    return _settings_instance
