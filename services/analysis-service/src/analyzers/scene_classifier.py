"""
Scene Classifier using CLIP for automatic image categorization
Provides flexible scene recognition without predefined prompts
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)

try:
    import clip
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("CLIP not available. Scene classification will be disabled.")

class SceneClassifier:
    """Flexible scene classifier using CLIP for automatic image categorization"""
    
    def __init__(self):
        if not CLIP_AVAILABLE:
            self.available = False
            return
            
        self.available = True
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            # Load CLIP model
            self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
            logger.info(f"✅ CLIP model loaded successfully on {self.device}")
            
            # Generic scene categories that work for most images
            self.generic_scenes = [
                "a person or people",
                "an animal or pet", 
                "a vehicle like car or truck",
                "a building or architecture",
                "nature like trees or landscape",
                "food or dining",
                "an event or celebration",
                "a sport or activity",
                "technology or electronics",
                "art or creative work",
                "indoor scene",
                "outdoor scene"
            ]
            
            # More specific scenes for better categorization
            self.specific_scenes = [
                "wedding ceremony with bride and groom",
                "birthday party with cake",
                "car driving on road",
                "mountain landscape",
                "beach with ocean",
                "city street with buildings",
                "family gathering",
                "restaurant dining",
                "sports game or match",
                "concert or music event",
                "graduation ceremony",
                "business meeting",
                "vacation or travel",
                "pets like dogs or cats",
                "children playing",
                "office or workspace",
                "garden or flowers",
                "sunset or sunrise",
                "food preparation or cooking",
                "shopping or retail"
            ]
            
            # We'll tokenize on-demand to avoid device issues
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize CLIP: {e}")
            self.available = False
    
    async def classify_scene(self, image_path: str) -> Dict[str, Any]:
        """
        Classify scene in image using CLIP
        Returns both generic and specific scene classifications
        """
        if not self.available:
            return {
                'available': False,
                'error': 'CLIP not available'
            }
        
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                # Encode image
                image_features = self.model.encode_image(image_input)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                # Tokenize and encode generic scenes
                generic_text = clip.tokenize(self.generic_scenes).to(self.device)
                generic_text_features = self.model.encode_text(generic_text)
                generic_text_features = generic_text_features / generic_text_features.norm(dim=-1, keepdim=True)
                
                # Get generic scene classification
                generic_similarities = (image_features @ generic_text_features.T).softmax(dim=-1)
                generic_top3 = generic_similarities[0].topk(3)
                
                # Tokenize and encode specific scenes
                specific_text = clip.tokenize(self.specific_scenes).to(self.device)
                specific_text_features = self.model.encode_text(specific_text)
                specific_text_features = specific_text_features / specific_text_features.norm(dim=-1, keepdim=True)
                
                # Get specific scene classification
                specific_similarities = (image_features @ specific_text_features.T).softmax(dim=-1)
                specific_top3 = specific_similarities[0].topk(3)
                
                # Format results
                generic_results = []
                for i, score in zip(generic_top3.indices, generic_top3.values):
                    generic_results.append({
                        'scene': self.generic_scenes[i.item()],
                        'confidence': score.item()
                    })
                
                specific_results = []
                for i, score in zip(specific_top3.indices, specific_top3.values):
                    specific_results.append({
                        'scene': self.specific_scenes[i.item()],
                        'confidence': score.item()
                    })
                
                # Extract scene tags
                scene_tags = self._extract_scene_tags(generic_results, specific_results)
                
                # Determine primary scene type
                primary_scene = self._determine_primary_scene(generic_results, specific_results)
                
                return {
                    'available': True,
                    'primary_scene': primary_scene,
                    'generic_scenes': generic_results,
                    'specific_scenes': specific_results,
                    'scene_tags': scene_tags,
                    'confidence': max(generic_results[0]['confidence'], specific_results[0]['confidence'])
                }
                
        except Exception as e:
            logger.error(f"❌ Scene classification error: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def _extract_scene_tags(self, generic_results: List[Dict], specific_results: List[Dict]) -> List[str]:
        """Extract relevant tags from scene classifications"""
        tags = set()
        
        # Add tags from top generic scenes
        for result in generic_results[:2]:
            scene = result['scene'].lower()
            if 'person' in scene or 'people' in scene:
                tags.add('people')
            elif 'animal' in scene or 'pet' in scene:
                tags.add('animals')
            elif 'vehicle' in scene or 'car' in scene:
                tags.add('vehicles')
            elif 'building' in scene or 'architecture' in scene:
                tags.add('architecture')
            elif 'nature' in scene or 'landscape' in scene:
                tags.add('nature')
            elif 'food' in scene or 'dining' in scene:
                tags.add('food')
            elif 'event' in scene or 'celebration' in scene:
                tags.add('events')
            elif 'sport' in scene or 'activity' in scene:
                tags.add('sports')
            elif 'indoor' in scene:
                tags.add('indoor')
            elif 'outdoor' in scene:
                tags.add('outdoor')
        
        # Add specific tags
        for result in specific_results[:2]:
            scene = result['scene'].lower()
            if 'wedding' in scene:
                tags.add('wedding')
            elif 'birthday' in scene:
                tags.add('birthday')
            elif 'car' in scene or 'driving' in scene:
                tags.add('transportation')
            elif 'mountain' in scene or 'landscape' in scene:
                tags.add('landscape')
            elif 'beach' in scene or 'ocean' in scene:
                tags.add('beach')
            elif 'city' in scene or 'street' in scene:
                tags.add('urban')
            elif 'family' in scene:
                tags.add('family')
            elif 'restaurant' in scene or 'dining' in scene:
                tags.add('dining')
            elif 'sport' in scene or 'game' in scene:
                tags.add('sports')
            elif 'concert' in scene or 'music' in scene:
                tags.add('music')
        
        return list(tags)
    
    def _determine_primary_scene(self, generic_results: List[Dict], specific_results: List[Dict]) -> Dict[str, Any]:
        """Determine the most likely primary scene"""
        # Use the highest confidence result
        if specific_results[0]['confidence'] > generic_results[0]['confidence']:
            return {
                'type': 'specific',
                'scene': specific_results[0]['scene'],
                'confidence': specific_results[0]['confidence']
            }
        else:
            return {
                'type': 'generic', 
                'scene': generic_results[0]['scene'],
                'confidence': generic_results[0]['confidence']
            }
    
    async def classify_scene_from_base64(self, base64_image: str) -> Dict[str, Any]:
        """Classify scene from base64 encoded image"""
        if not self.available:
            return {
                'available': False,
                'error': 'CLIP not available'
            }
        
        try:
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            
            # Use same classification logic
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                # Tokenize and encode generic scenes
                generic_text = clip.tokenize(self.generic_scenes).to(self.device)
                generic_text_features = self.model.encode_text(generic_text)
                generic_text_features = generic_text_features / generic_text_features.norm(dim=-1, keepdim=True)
                
                # Get generic scene classification
                generic_similarities = (image_features @ generic_text_features.T).softmax(dim=-1)
                generic_top3 = generic_similarities[0].topk(3)
                
                # Tokenize and encode specific scenes
                specific_text = clip.tokenize(self.specific_scenes).to(self.device)
                specific_text_features = self.model.encode_text(specific_text)
                specific_text_features = specific_text_features / specific_text_features.norm(dim=-1, keepdim=True)
                
                # Get specific scene classification
                specific_similarities = (image_features @ specific_text_features.T).softmax(dim=-1)
                specific_top3 = specific_similarities[0].topk(3)
                
                generic_results = []
                for i, score in zip(generic_top3.indices, generic_top3.values):
                    generic_results.append({
                        'scene': self.generic_scenes[i.item()],
                        'confidence': score.item()
                    })
                
                specific_results = []
                for i, score in zip(specific_top3.indices, specific_top3.values):
                    specific_results.append({
                        'scene': self.specific_scenes[i.item()],
                        'confidence': score.item()
                    })
                
                scene_tags = self._extract_scene_tags(generic_results, specific_results)
                primary_scene = self._determine_primary_scene(generic_results, specific_results)
                
                return {
                    'available': True,
                    'primary_scene': primary_scene,
                    'generic_scenes': generic_results,
                    'specific_scenes': specific_results,
                    'scene_tags': scene_tags,
                    'confidence': max(generic_results[0]['confidence'], specific_results[0]['confidence'])
                }
                
        except Exception as e:
            logger.error(f"❌ Base64 scene classification error: {e}")
            return {
                'available': False,
                'error': str(e)
            }
