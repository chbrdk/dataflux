#!/usr/bin/env python3
"""
Memory Management Utilities für Video Analysis Pipeline
"""

import logging
import psutil
import os
import gc
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory statistics"""
    total_gb: float
    available_gb: float
    used_gb: float
    usage_percent: float
    process_memory_mb: float

# Model Size Registry (in GB)
MODEL_SIZES = {
    # YOLO Models
    "yolo_nano": 0.3,
    "yolo_small": 0.5,
    "yolo_medium": 1.0,
    "yolo_large": 2.0,
    "yolo_xlarge": 3.0,
    
    # CLIP Models
    "clip_base": 0.5,
    "clip_large": 1.5,
    "clip_huge": 3.0,
    
    # Whisper Models
    "whisper_tiny": 0.4,
    "whisper_base": 0.7,
    "whisper_small": 1.0,
    "whisper_medium": 1.5,
    "whisper_large": 3.0,
    "whisper_large_v2": 3.0,
    "whisper_large_v3": 3.0,
    
    # Face Recognition
    "facenet": 0.8,
    "mtcnn": 0.2,
    "retinaface": 0.5,
    
    # Pose Estimation
    "mediapipe_holistic": 0.2,
    "openpose": 1.5,
    
    # Depth Estimation
    "depth_anything": 1.2,
    "midas": 1.0,
    "dpt": 1.5,
    
    # Other Models
    "easyocr": 0.8,
    "paddleocr": 1.0,
    "tesseract": 0.1,
}

def get_available_ram() -> float:
    """Get available RAM in GB"""
    try:
        memory = psutil.virtual_memory()
        return memory.available / (1024**3)
    except Exception as e:
        logger.error(f"Failed to get available RAM: {e}")
        return 0.0

def get_total_ram() -> float:
    """Get total RAM in GB"""
    try:
        memory = psutil.virtual_memory()
        return memory.total / (1024**3)
    except Exception as e:
        logger.error(f"Failed to get total RAM: {e}")
        return 0.0

def get_process_memory() -> float:
    """Get current process memory usage in MB"""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024**2)
    except Exception as e:
        logger.error(f"Failed to get process memory: {e}")
        return 0.0

def get_memory_stats() -> MemoryStats:
    """Get comprehensive memory statistics"""
    try:
        memory = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        
        return MemoryStats(
            total_gb=memory.total / (1024**3),
            available_gb=memory.available / (1024**3),
            used_gb=(memory.total - memory.available) / (1024**3),
            usage_percent=memory.percent / 100.0,
            process_memory_mb=process.memory_info().rss / (1024**2)
        )
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return MemoryStats(0.0, 0.0, 0.0, 0.0, 0.0)

def estimate_model_size(model_name: str) -> float:
    """Estimate model size in GB"""
    return MODEL_SIZES.get(model_name, 1.0)  # Default to 1GB if unknown

def can_load_model(model_name: str, safety_factor: float = 1.5) -> bool:
    """Check if we can load a model without running out of memory"""
    try:
        model_size = estimate_model_size(model_name)
        available_ram = get_available_ram()
        
        # Need safety_factor * model_size GB free
        required_ram = model_size * safety_factor
        
        if available_ram < required_ram:
            logger.warning(
                f"Cannot load {model_name}: need {required_ram:.1f}GB, "
                f"have {available_ram:.1f}GB available"
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking if model can be loaded: {e}")
        return False

def get_memory_warning_level() -> str:
    """Get memory warning level"""
    try:
        usage_percent = psutil.virtual_memory().percent / 100.0
        
        if usage_percent >= 0.95:
            return "critical"
        elif usage_percent >= 0.90:
            return "high"
        elif usage_percent >= 0.80:
            return "warning"
        else:
            return "normal"
            
    except Exception as e:
        logger.error(f"Failed to get memory warning level: {e}")
        return "unknown"

def log_memory_stats(context: str = ""):
    """Log current memory statistics"""
    try:
        stats = get_memory_stats()
        warning_level = get_memory_warning_level()
        
        logger.info(
            f"Memory Stats {context}: "
            f"Total: {stats.total_gb:.1f}GB, "
            f"Available: {stats.available_gb:.1f}GB, "
            f"Used: {stats.used_gb:.1f}GB ({stats.usage_percent:.1%}), "
            f"Process: {stats.process_memory_mb:.1f}MB, "
            f"Level: {warning_level}"
        )
        
        # Log warning if memory usage is high
        if warning_level in ["warning", "high", "critical"]:
            logger.warning(f"High memory usage detected: {stats.usage_percent:.1%}")
            
    except Exception as e:
        logger.error(f"Failed to log memory stats: {e}")

def force_garbage_collection():
    """Force garbage collection to free memory"""
    try:
        collected = gc.collect()
        logger.debug(f"Garbage collection freed {collected} objects")
        return collected
    except Exception as e:
        logger.error(f"Failed to run garbage collection: {e}")
        return 0

def get_recommended_tier() -> str:
    """Get recommended tier based on available RAM"""
    try:
        total_ram = get_total_ram()
        
        if total_ram >= 48:
            return "pro"
        elif total_ram >= 24:
            return "standard"
        else:
            return "lite"
            
    except Exception as e:
        logger.error(f"Failed to get recommended tier: {e}")
        return "lite"

def check_memory_health() -> Dict[str, Any]:
    """Comprehensive memory health check"""
    try:
        stats = get_memory_stats()
        warning_level = get_memory_warning_level()
        recommended_tier = get_recommended_tier()
        
        return {
            "healthy": warning_level in ["normal", "warning"],
            "warning_level": warning_level,
            "recommended_tier": recommended_tier,
            "stats": {
                "total_gb": stats.total_gb,
                "available_gb": stats.available_gb,
                "used_gb": stats.used_gb,
                "usage_percent": stats.usage_percent,
                "process_memory_mb": stats.process_memory_mb
            },
            "recommendations": _get_memory_recommendations(warning_level, stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to check memory health: {e}")
        return {
            "healthy": False,
            "warning_level": "unknown",
            "error": str(e)
        }

def _get_memory_recommendations(warning_level: str, stats: MemoryStats) -> List[str]:
    """Get memory management recommendations"""
    recommendations = []
    
    if warning_level == "critical":
        recommendations.extend([
            "CRITICAL: Memory usage is extremely high (>95%)",
            "Immediately unload unused models",
            "Consider reducing batch sizes",
            "Restart the service if necessary"
        ])
    elif warning_level == "high":
        recommendations.extend([
            "High memory usage detected (>90%)",
            "Consider unloading least recently used models",
            "Monitor memory usage closely"
        ])
    elif warning_level == "warning":
        recommendations.extend([
            "Memory usage is elevated (>80%)",
            "Consider proactive model cleanup",
            "Monitor for memory leaks"
        ])
    else:
        recommendations.append("Memory usage is normal")
    
    # Add tier-specific recommendations
    if stats.total_gb < 16:
        recommendations.append("Consider upgrading to more RAM for better performance")
    elif stats.total_gb >= 48:
        recommendations.append("System has sufficient RAM for pro-tier features")
    
    return recommendations

def monitor_memory_usage(interval_seconds: int = 30):
    """Monitor memory usage and log warnings"""
    import time
    
    logger.info(f"Starting memory monitoring (interval: {interval_seconds}s)")
    
    while True:
        try:
            warning_level = get_memory_warning_level()
            
            if warning_level in ["warning", "high", "critical"]:
                log_memory_stats("MONITOR")
            
            time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            logger.info("Memory monitoring stopped")
            break
        except Exception as e:
            logger.error(f"Error in memory monitoring: {e}")
            time.sleep(interval_seconds)

# Memory cleanup utilities
def cleanup_pytorch_cache():
    """Cleanup PyTorch cache if available"""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("PyTorch CUDA cache cleared")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to cleanup PyTorch cache: {e}")

def cleanup_tensorflow_cache():
    """Cleanup TensorFlow cache if available"""
    try:
        import tensorflow as tf
        tf.keras.backend.clear_session()
        logger.debug("TensorFlow session cleared")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to cleanup TensorFlow cache: {e}")

def full_memory_cleanup():
    """Perform full memory cleanup"""
    logger.info("Performing full memory cleanup")
    
    # Force garbage collection
    collected = force_garbage_collection()
    
    # Cleanup framework caches
    cleanup_pytorch_cache()
    cleanup_tensorflow_cache()
    
    # Log final stats
    log_memory_stats("AFTER CLEANUP")
    
    return collected
