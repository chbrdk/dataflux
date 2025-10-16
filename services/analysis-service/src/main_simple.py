#!/usr/bin/env python3
"""
DataFlux Analysis Service - Simplified Version for Testing
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add analyzers to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append('/app/analyzers')
sys.path.append('/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service')

try:
    from analyzers.image_analyzer import ImageAnalyzer
    IMAGE_ANALYZER_AVAILABLE = True
except ImportError:
    IMAGE_ANALYZER_AVAILABLE = False

try:
    from analyzers.docling_analyzer import DoclingAnalyzer
    DOCLING_ANALYZER_AVAILABLE = True
    print("✅ DoclingAnalyzer import erfolgreich!")
except ImportError as e:
    DOCLING_ANALYZER_AVAILABLE = False
    print(f"❌ DoclingAnalyzer import fehlgeschlagen: {e}")

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="DataFlux Analysis Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class AnalyzeRequest(BaseModel):
    file_path: str

# Initialize analyzers
image_analyzer = None
docling_analyzer = None

if IMAGE_ANALYZER_AVAILABLE:
    try:
        image_analyzer = ImageAnalyzer()
        logger.info("Image analyzer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize image analyzer: {e}")
        image_analyzer = None

if DOCLING_ANALYZER_AVAILABLE:
    try:
        docling_analyzer = DoclingAnalyzer()
        logger.info("Docling analyzer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Docling analyzer: {e}")
        docling_analyzer = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "image_analyzer": "available" if image_analyzer else "unavailable",
            "docling_analyzer": "available" if docling_analyzer else "unavailable"
        }
    }

@app.post("/api/v1/analyze/image")
async def analyze_image(request: AnalyzeRequest):
    """Analyze an image file"""
    try:
        if not image_analyzer:
            raise HTTPException(status_code=503, detail="Image analyzer not available")
        
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Analyze the image
        asset_data = {"filename": os.path.basename(request.file_path)}
        result = await image_analyzer.analyze(request.file_path, asset_data)
        
        return {
            "status": "success",
            "file_path": request.file_path,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analyze/document")
async def analyze_document(request: AnalyzeRequest):
    """Analyze a document file using Docling"""
    try:
        if not docling_analyzer:
            raise HTTPException(status_code=503, detail="Docling analyzer not available")
        
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Analyze the document
        asset_data = {
            "id": str(uuid.uuid4()),
            "filename": os.path.basename(request.file_path),
            "mime_type": "text/html"  # Default, could be detected
        }
        result = await docling_analyzer.analyze(request.file_path, asset_data)
        
        return {
            "status": "success",
            "file_path": request.file_path,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2014)