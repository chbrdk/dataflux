#!/usr/bin/env python3
"""
Claude Vision Mock API - Für Demo-Zwecke
"""

import asyncio
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def analyze_image_with_claude_mock(image_path: str) -> Dict[str, Any]:
    """Mock Claude Vision Analysis für Demo"""
    try:
        logger.info(f"🤖 Mock Claude Vision analysis for {image_path}")
        
        # Simuliere Verarbeitungszeit
        await asyncio.sleep(2)
        
        # Mock-Analyse basierend auf Dateinamen
        filename = image_path.split('/')[-1].lower()
        
        if 'deepface' in filename:
            analysis_data = {
                "hauptinhalt": "Porträtaufnahme einer Person",
                "szenenbeschreibung": "Professionelle Porträtaufnahme mit neutralem Hintergrund, optimale Beleuchtung für Gesichtserkennung",
                "objekte": ["Person", "Hintergrund", "Beleuchtung"],
                "personen": "Eine Person im Vordergrund, professionell fotografiert",
                "farben": {
                    "hauptfarben": ["Hautton", "Neutral", "Grau"],
                    "farbharmonie": "Neutrale, professionelle Farbgebung"
                },
                "komposition": {
                    "bildaufbau": "Zentrierte Komposition mit Fokus auf das Gesicht",
                    "perspektive": "Frontale Aufnahme",
                    "regel_der_drittel": "Gesicht ist zentriert positioniert"
                },
                "stimmung": "Professionell, neutral, für Identifikation optimiert",
                "technische_aspekte": {
                    "schaerfe": "Sehr scharf, optimiert für Gesichtserkennung",
                    "belichtung": "Ausgewogen, keine Über- oder Unterbelichtung",
                    "kontrast": "Guter Kontrast für Gesichtserkennung"
                },
                "text": [],
                "tags": ["portrait", "face", "professional", "identification"]
            }
        elif 'test' in filename:
            analysis_data = {
                "hauptinhalt": "Testbild für Bildanalyse",
                "szenenbeschreibung": "Ein Testbild, das für die Validierung von Bildanalysesystemen verwendet wird",
                "objekte": ["Testobjekt", "Hintergrund"],
                "personen": "Keine Personen erkennbar",
                "farben": {
                    "hauptfarben": ["Verschiedene Testfarben"],
                    "farbharmonie": "Testfarben für Validierung"
                },
                "komposition": {
                    "bildaufbau": "Einfache Testkomposition",
                    "perspektive": "Standard-Testperspektive",
                    "regel_der_drittel": "Nicht angewendet"
                },
                "stimmung": "Neutral, für Tests optimiert",
                "technische_aspekte": {
                    "schaerfe": "Testschärfe",
                    "belichtung": "Standard-Testbelichtung",
                    "kontrast": "Testkontrast"
                },
                "text": [],
                "tags": ["test", "validation", "analysis"]
            }
        else:
            analysis_data = {
                "hauptinhalt": "Unbekanntes Bild analysiert",
                "szenenbeschreibung": "Claude Vision hat das Bild analysiert und eine detaillierte Beschreibung erstellt",
                "objekte": ["Verschiedene Objekte erkennbar"],
                "personen": "Personen möglicherweise vorhanden",
                "farben": {
                    "hauptfarben": ["Verschiedene Farben"],
                    "farbharmonie": "Ausgewogene Farbgebung"
                },
                "komposition": {
                    "bildaufbau": "Interessante Bildkomposition",
                    "perspektive": "Gute Perspektive",
                    "regel_der_drittel": "Möglicherweise angewendet"
                },
                "stimmung": "Positive Stimmung",
                "technische_aspekte": {
                    "schaerfe": "Gute Schärfe",
                    "belichtung": "Ausgewogene Belichtung",
                    "kontrast": "Guter Kontrast"
                },
                "text": [],
                "tags": ["analysis", "claude-vision", "ai-generated"]
            }
        
        logger.info("✅ Mock Claude Vision analysis completed successfully")
        
        return {
            "status": "completed",
            "analyzer": "claude_vision_mock",
            "model": "claude-3-5-sonnet-mock",
            "max_megapixels": 5.0,
            "analysis": analysis_data
        }
        
    except Exception as e:
        logger.error(f"❌ Mock Claude Vision analysis failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }
