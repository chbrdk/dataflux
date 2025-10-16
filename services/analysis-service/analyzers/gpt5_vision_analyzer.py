"""
GPT-5 Vision Analyzer - Nutzt OpenAI's GPT-5 und GPT-5-nano für umfassende Bildanalyse
"""

import asyncio
import base64
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import httpx
from PIL import Image
import io

logger = logging.getLogger(__name__)

class GPT5VisionAnalyzer:
    """Analyzer für OpenAI's GPT-5 und GPT-5-nano Vision API mit Bildvorverarbeitung"""
    
    def __init__(self, api_key: Optional[str] = None, use_nano: bool = True):
        self.api_key = api_key or self._get_api_key()
        self.use_nano = use_nano
        self.model = "gpt-5-nano" if use_nano else "gpt-5"  # Neueste OpenAI Vision Modelle
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
        # GPT-5 Vision Limits (erweiterte Fähigkeiten)
        self.max_image_size = 50 * 1024 * 1024  # 50MB für GPT-5
        self.supported_formats = ['jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp', 'tiff']
        
        logger.info(f"✅ GPT-5 Vision Analyzer initialized (Model: {self.model})")
    
    def _get_api_key(self) -> str:
        """Holt OpenAI API Key aus Umgebungsvariablen"""
        import os
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return api_key
    
    def _resize_image_for_gpt5(self, image_path: str) -> Optional[str]:
        """
        Bild für GPT-5 vorbereiten und als Base64 kodieren
        GPT-5 unterstützt größere Bilder und mehr Formate als GPT-4o
        """
        try:
            with Image.open(image_path) as img:
                # Konvertiere zu RGB falls nötig
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # GPT-5 kann noch größere Bilder verarbeiten
                max_dimension = 4096 if not self.use_nano else 2048  # nano ist effizienter
                
                if img.width > max_dimension or img.height > max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
                # Speichere als JPEG für kleinere Dateigröße
                buffer = io.BytesIO()
                quality = 90 if not self.use_nano else 85  # nano verwendet niedrigere Qualität
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                buffer.seek(0)
                
                # Prüfe Dateigröße
                if buffer.getbuffer().nbytes > self.max_image_size:
                    # Nochmal komprimieren
                    quality = 80 if not self.use_nano else 75
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    buffer.seek(0)
                
                # Base64 kodieren
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                logger.info(f"✅ Bild für GPT-5 vorbereitet: {img.width}x{img.height}, {len(image_base64)} chars")
                return image_base64
                
        except Exception as e:
            logger.error(f"❌ Bildvorverarbeitung fehlgeschlagen: {e}")
            return None
    
    async def _analyze_with_gpt5(self, image_base64: str, filename: str) -> Dict[str, Any]:
        """
        Sendet Bild an GPT-5 Vision API und erhält umfassende Analyse
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Erweiterter Prompt für GPT-5 Vision (noch intelligenter)
            prompt = f"""
            Analysiere dieses Bild ({filename}) mit GPT-5's fortschrittlichen Vision-Fähigkeiten:

            1. **Erweiterte Objektidentifikation**: Erkenne Objekte, Personen, Tiere, Fahrzeuge, Gebäude mit hoher Präzision
            2. **Kontextuelle Szene-Analyse**: Verstehe komplexe Szenen, Beziehungen zwischen Objekten und räumliche Anordnung
            3. **Aktivitäts-Erkennung**: Identifiziere spezifische Aktivitäten, Bewegungen und Interaktionen
            4. **Emotionale Intelligenz**: Erkenne Emotionen, Stimmungen und zwischenmenschliche Dynamiken
            5. **Technische Bildanalyse**: Beleuchtung, Komposition, Farbpsychologie, Bildqualität
            6. **Text-Erkennung und OCR**: Transkribiere alle sichtbaren Texte mit hoher Genauigkeit
            7. **Kulturelle und soziale Kontexte**: Erkenne kulturelle Hinweise, soziale Situationen
            8. **Besondere Merkmale**: Ungewöhnliche Elemente, interessante Details, künstlerische Aspekte
            9. **Zusammenfassung und Insights**: Intelligente Zusammenfassung mit tiefen Einblicken

            Nutze GPT-5's erweiterte Reasoning-Fähigkeiten für eine besonders detaillierte und intelligente Analyse.
            Antworte strukturiert und detailliert auf Deutsch.
            """
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"  # GPT-5 unterstützt noch höhere Detail-Level
                                }
                            }
                        ]
                    }
                ],
                "max_completion_tokens": 3000 if not self.use_nano else 2000,  # GPT-5 verwendet max_completion_tokens
                "temperature": 1.0 if self.use_nano else 0.2,  # nano unterstützt nur temperature=1
            }
            
            async with httpx.AsyncClient(timeout=90.0) as client:  # GPT-5 kann länger brauchen
                response = await client.post(self.base_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    analysis_text = result['choices'][0]['message']['content']
                    
                    logger.info(f"✅ GPT-5 Vision Analyse erfolgreich ({self.model})")
                    
                    return {
                        "status": "completed",
                        "analysis": analysis_text,
                        "model": self.model,
                        "tokens_used": result.get('usage', {}).get('total_tokens', 0),
                        "filename": filename,
                        "is_nano": self.use_nano
                    }
                else:
                    error_text = response.text
                    logger.error(f"❌ GPT-5 API error {response.status_code}: {error_text}")
                    return {
                        "status": "error",
                        "error": f"API error {response.status_code}: {error_text}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ GPT-5 Vision API request failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Hauptmethode: Analysiert Bild mit GPT-5 Vision
        """
        try:
            logger.info(f"🔍 Starting GPT-5 Vision analysis for {image_path}")
            
            # 1. Bildvorverarbeitung
            image_base64 = self._resize_image_for_gpt5(image_path)
            if not image_base64:
                return {
                    "status": "error",
                    "error": "Bildvorverarbeitung fehlgeschlagen"
                }
            
            # 2. Analyse mit GPT-5
            filename = Path(image_path).name
            analysis_result = await self._analyze_with_gpt5(image_base64, filename)
            
            if analysis_result.get('status') == 'completed':
                return {
                    "status": "completed",
                    "analyzer": "gpt5_vision",
                    "model": self.model,
                    "analysis": analysis_result['analysis'],
                    "tokens_used": analysis_result.get('tokens_used', 0),
                    "filename": filename,
                    "is_nano": self.use_nano,
                    "metadata": {
                        "analyzer": "gpt5_vision_analyzer",
                        "model": self.model,
                        "api_version": "2024-12-01",
                        "is_nano": self.use_nano
                    }
                }
            else:
                logger.error(f"❌ GPT-5 Vision analysis failed: {analysis_result.get('error', 'Unknown error')}")
                return {
                    "status": "error",
                    "analyzer": "gpt5_vision",
                    "error": analysis_result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"❌ GPT-5 Vision analysis failed: {e}")
            return {
                "status": "error",
                "analyzer": "gpt5_vision",
                "error": str(e)
            }

# Verfügbarkeitsprüfung
GPT5_VISION_AVAILABLE = True

def create_gpt5_vision_analyzer(use_nano: bool = True) -> Optional[GPT5VisionAnalyzer]:
    """Factory function to create GPT-5 Vision Analyzer"""
    try:
        import os
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return GPT5VisionAnalyzer(api_key, use_nano=use_nano)
        else:
            logger.warning("⚠️ OPENAI_API_KEY not found in environment")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to create GPT-5 Vision Analyzer: {e}")
        return None
