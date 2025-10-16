#!/usr/bin/env python3
"""
Claude Vision REST API Endpoint
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile
import os
import logging
from typing import Dict, Any
from claude_vision_api import analyze_image_with_claude

logger = logging.getLogger(__name__)

# Router für Claude Vision Endpoints
claude_router = APIRouter(prefix="/api/v1/claude", tags=["claude-vision"])

@claude_router.post("/analyze")
async def analyze_image_claude(file: UploadFile = File(...)) -> JSONResponse:
    """
    Claude Vision Analysis für hochgeladenes Bild
    """
    try:
        logger.info(f"📸 Received image for Claude analysis: {file.filename}")
        
        # Temporäre Datei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            # Bildinhalt schreiben
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Claude Vision Analysis
            result = await analyze_image_with_claude(temp_file_path)
            
            # Temporäre Datei löschen
            os.unlink(temp_file_path)
            
            if result.get("status") == "completed":
                logger.info("✅ Claude Vision analysis completed successfully")
                return JSONResponse(content={
                    "success": True,
                    "data": result,
                    "message": "Claude Vision analysis completed"
                })
            else:
                logger.error(f"❌ Claude Vision analysis failed: {result.get('error', 'Unknown error')}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": result.get("error", "Analysis failed"),
                        "message": "Claude Vision analysis failed"
                    }
                )
                
        except Exception as e:
            # Temporäre Datei löschen bei Fehler
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise e
            
    except Exception as e:
        logger.error(f"❌ Claude Vision endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@claude_router.post("/analyze-path")
async def analyze_image_path_claude(image_path: str) -> JSONResponse:
    """
    Claude Vision Analysis für Bild-Pfad
    """
    try:
        logger.info(f"📸 Analyzing image path: {image_path}")
        
        # Prüfen ob Datei existiert
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        # Claude Vision Analysis
        result = await analyze_image_with_claude(image_path)
        
        if result.get("status") == "completed":
            logger.info("✅ Claude Vision analysis completed successfully")
            return JSONResponse(content={
                "success": True,
                "data": result,
                "message": "Claude Vision analysis completed"
            })
        else:
            logger.error(f"❌ Claude Vision analysis failed: {result.get('error', 'Unknown error')}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": result.get("error", "Analysis failed"),
                    "message": "Claude Vision analysis failed"
                }
            )
            
    except Exception as e:
        logger.error(f"❌ Claude Vision endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@claude_router.get("/health")
async def claude_health_check() -> JSONResponse:
    """
    Health Check für Claude Vision Service
    """
    return JSONResponse(content={
        "status": "healthy",
        "service": "claude-vision-api",
        "model": "claude-sonnet-4-5-20250929",
        "max_megapixels": 5.0
    })
