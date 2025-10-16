#!/usr/bin/env python3
"""
Model Manager mit Smart Loading, Memory Tracking und Auto-Unload
"""

import asyncio
import logging
import time
import weakref
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import psutil
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """Informationen über ein geladenes Model"""
    name: str
    model: Any
    size_gb: float
    loaded_at: float
    last_used: float
    usage_count: int
    tier: str

class ModelManager:
    """Intelligenter Model Manager mit Memory Management und Tier System"""
    
    def __init__(self):
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.model_registry: Dict[str, Dict[str, Any]] = {}
        self.current_tier: Optional[str] = None
        self.max_memory_gb: float = 0.0
        self.memory_threshold: float = 0.8  # 80% RAM usage threshold
        
        # Initialize model registry
        self._initialize_model_registry()
        
        # Detect system capabilities
        self._detect_system_capabilities()
        
        logger.info(f"ModelManager initialized - Tier: {self.current_tier}, Max RAM: {self.max_memory_gb:.1f}GB")
    
    def _initialize_model_registry(self):
        """Initialize registry of available models per tier"""
        self.model_registry = {
            "lite": {
                "yolo": {
                    "name": "yolo_nano",
                    "size_gb": 0.3,
                    "module": "ultralytics",
                    "class": "YOLO",
                    "args": ["yolov8n.pt"]
                },
                "clip": {
                    "name": "clip_base",
                    "size_gb": 0.5,
                    "module": "transformers",
                    "class": "CLIPModel",
                    "args": ["openai/clip-vit-base-patch32"]
                },
                "whisper": {
                    "name": "whisper_small",
                    "size_gb": 1.0,
                    "module": "whisper",
                    "class": "load_model",
                    "args": ["small"]
                }
            },
            "standard": {
                "yolo": {
                    "name": "yolo_medium",
                    "size_gb": 1.0,
                    "module": "ultralytics",
                    "class": "YOLO",
                    "args": ["yolov8m.pt"]
                },
                "clip": {
                    "name": "clip_large",
                    "size_gb": 1.5,
                    "module": "transformers",
                    "class": "CLIPModel",
                    "args": ["openai/clip-vit-large-patch14"]
                },
                "whisper": {
                    "name": "whisper_medium",
                    "size_gb": 1.5,
                    "module": "whisper",
                    "class": "load_model",
                    "args": ["medium"]
                },
                "facenet": {
                    "name": "facenet",
                    "size_gb": 0.8,
                    "module": "facenet_pytorch",
                    "class": "MTCNN",
                    "args": []
                }
            },
            "pro": {
                "yolo": {
                    "name": "yolo_large",
                    "size_gb": 2.0,
                    "module": "ultralytics",
                    "class": "YOLO",
                    "args": ["yolov8l.pt"]
                },
                "clip": {
                    "name": "clip_large",
                    "size_gb": 1.5,
                    "module": "transformers",
                    "class": "CLIPModel",
                    "args": ["openai/clip-vit-large-patch14"]
                },
                "whisper": {
                    "name": "whisper_large",
                    "size_gb": 3.0,
                    "module": "whisper",
                    "class": "load_model",
                    "args": ["large-v3"]
                },
                "facenet": {
                    "name": "facenet",
                    "size_gb": 0.8,
                    "module": "facenet_pytorch",
                    "class": "MTCNN",
                    "args": []
                },
                "mediapipe": {
                    "name": "mediapipe_holistic",
                    "size_gb": 0.2,
                    "module": "mediapipe",
                    "class": "Holistic",
                    "args": []
                },
                "depth": {
                    "name": "depth_anything",
                    "size_gb": 1.2,
                    "module": "transformers",
                    "class": "DPTForDepthEstimation",
                    "args": ["Intel/dpt-large"]
                }
            }
        }
    
    def _detect_system_capabilities(self):
        """Detect available RAM and determine appropriate tier"""
        try:
            # Get available RAM in GB
            available_ram = psutil.virtual_memory().total / (1024**3)
            self.max_memory_gb = available_ram
            
            # Determine tier based on available RAM
            if available_ram >= 48:
                self.current_tier = "pro"
            elif available_ram >= 24:
                self.current_tier = "standard"
            else:
                self.current_tier = "lite"
                
            logger.info(f"System detected: {available_ram:.1f}GB RAM -> Tier: {self.current_tier}")
            
        except Exception as e:
            logger.warning(f"Failed to detect system capabilities: {e}")
            self.current_tier = "lite"
            self.max_memory_gb = 16.0
    
    def get_current_tier(self) -> str:
        """Get current tier"""
        return self.current_tier
    
    def get_available_ram_gb(self) -> float:
        """Get current available RAM in GB"""
        return psutil.virtual_memory().available / (1024**3)
    
    def get_memory_usage_percent(self) -> float:
        """Get current memory usage percentage"""
        return psutil.virtual_memory().percent / 100.0
    
    def can_load_model(self, model_name: str, tier: Optional[str] = None) -> bool:
        """Check if we can load a model without exceeding memory limits"""
        tier = tier or self.current_tier
        
        if tier not in self.model_registry:
            logger.warning(f"Unknown tier: {tier}")
            return False
        
        # Check if model exists in tier
        if model_name not in self.model_registry[tier]:
            logger.warning(f"Model {model_name} not available in tier {tier}")
            return False
        
        model_info = self.model_registry[tier][model_name]
        model_size = model_info["size_gb"]
        
        # Check current memory usage
        current_usage = self.get_memory_usage_percent()
        if current_usage > self.memory_threshold:
            logger.warning(f"Memory usage too high: {current_usage:.1%}")
            return False
        
        # Check if we have enough free RAM
        available_ram = self.get_available_ram_gb()
        if available_ram < model_size * 1.5:  # Need 1.5x model size free
            logger.warning(f"Not enough RAM: {available_ram:.1f}GB < {model_size * 1.5:.1f}GB")
            return False
        
        return True
    
    async def load_model(self, model_name: str, tier: Optional[str] = None) -> Any:
        """Load a model with lazy loading and memory management"""
        tier = tier or self.current_tier
        
        # Check if already loaded
        if model_name in self.loaded_models:
            model_info = self.loaded_models[model_name]
            model_info.last_used = time.time()
            model_info.usage_count += 1
            logger.info(f"Model {model_name} already loaded, returning cached instance")
            return model_info.model
        
        # Check if we can load the model
        if not self.can_load_model(model_name, tier):
            raise RuntimeError(f"Cannot load model {model_name} - insufficient memory or invalid tier")
        
        # Auto-cleanup if memory is getting tight
        await self._auto_cleanup_if_needed()
        
        # Load the model
        logger.info(f"Loading model {model_name} (tier: {tier})")
        start_time = time.time()
        
        try:
            model_config = self.model_registry[tier][model_name]
            model = await self._load_model_instance(model_config)
            
            # Store model info
            model_info = ModelInfo(
                name=model_name,
                model=model,
                size_gb=model_config["size_gb"],
                loaded_at=time.time(),
                last_used=time.time(),
                usage_count=1,
                tier=tier
            )
            
            self.loaded_models[model_name] = model_info
            
            load_time = time.time() - start_time
            logger.info(f"Model {model_name} loaded successfully in {load_time:.2f}s")
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    async def _load_model_instance(self, model_config: Dict[str, Any]) -> Any:
        """Load a specific model instance"""
        module_name = model_config["module"]
        class_name = model_config["class"]
        args = model_config.get("args", [])
        
        # Import module dynamically
        module = __import__(module_name, fromlist=[class_name])
        model_class = getattr(module, class_name)
        
        # Create model instance
        if args:
            model = model_class(*args)
        else:
            model = model_class()
        
        return model
    
    async def unload_model(self, model_name: str):
        """Explicitly unload a model"""
        if model_name not in self.loaded_models:
            logger.warning(f"Model {model_name} not loaded")
            return
        
        model_info = self.loaded_models[model_name]
        
        # Cleanup model resources
        try:
            if hasattr(model_info.model, 'close'):
                model_info.model.close()
            elif hasattr(model_info.model, 'cpu'):
                model_info.model.cpu()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            logger.info(f"Model {model_name} unloaded successfully")
            
        except Exception as e:
            logger.warning(f"Error unloading model {model_name}: {e}")
        
        finally:
            del self.loaded_models[model_name]
    
    async def _auto_cleanup_if_needed(self):
        """Auto-cleanup least recently used models if memory usage is high"""
        memory_usage = self.get_memory_usage_percent()
        
        if memory_usage > self.memory_threshold:
            logger.info(f"Memory usage high ({memory_usage:.1%}), starting auto-cleanup")
            
            # Sort models by last_used (oldest first)
            sorted_models = sorted(
                self.loaded_models.items(),
                key=lambda x: x[1].last_used
            )
            
            # Unload oldest models until memory usage drops
            for model_name, model_info in sorted_models:
                if memory_usage <= self.memory_threshold * 0.7:  # Stop at 70%
                    break
                
                logger.info(f"Auto-unloading model {model_name} (last used: {time.time() - model_info.last_used:.1f}s ago)")
                await self.unload_model(model_name)
                
                # Recheck memory usage
                memory_usage = self.get_memory_usage_percent()
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return list(self.loaded_models.keys())
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get information about a loaded model"""
        return self.loaded_models.get(model_name)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        total_loaded_size = sum(info.size_gb for info in self.loaded_models.values())
        
        return {
            "current_tier": self.current_tier,
            "max_memory_gb": self.max_memory_gb,
            "available_ram_gb": self.get_available_ram_gb(),
            "memory_usage_percent": self.get_memory_usage_percent(),
            "loaded_models": len(self.loaded_models),
            "total_loaded_size_gb": total_loaded_size,
            "models": {
                name: {
                    "size_gb": info.size_gb,
                    "loaded_at": info.loaded_at,
                    "last_used": info.last_used,
                    "usage_count": info.usage_count,
                    "tier": info.tier
                }
                for name, info in self.loaded_models.items()
            }
        }
    
    @asynccontextmanager
    async def load(self, model_name: str, tier: Optional[str] = None):
        """Context manager for automatic model cleanup"""
        model = await self.load_model(model_name, tier)
        try:
            yield model
        finally:
            # Note: We don't auto-unload here as the model might be used again soon
            # The auto-cleanup will handle memory pressure
            pass
    
    async def cleanup_all(self):
        """Cleanup all loaded models"""
        logger.info("Cleaning up all loaded models")
        
        for model_name in list(self.loaded_models.keys()):
            await self.unload_model(model_name)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logger.info("All models cleaned up")

# Global instance
_model_manager_instance: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    """Get global ModelManager instance"""
    global _model_manager_instance
    if _model_manager_instance is None:
        _model_manager_instance = ModelManager()
    return _model_manager_instance

async def cleanup_model_manager():
    """Cleanup global ModelManager instance"""
    global _model_manager_instance
    if _model_manager_instance:
        await _model_manager_instance.cleanup_all()
        _model_manager_instance = None
