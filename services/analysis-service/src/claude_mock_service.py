#!/usr/bin/env python3
"""
Claude Vision Mock Service - Für Demo-Zwecke
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from claude_mock_api import analyze_image_with_claude_mock

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Claude Vision Mock Service",
    description="Mock Claude Vision Analysis API für Demo",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/claude/analyze-path")
async def analyze_image_path_claude_mock(image_path: str) -> JSONResponse:
    """
    Mock Claude Vision Analysis für Bild-Pfad
    """
    try:
        logger.info(f"📸 Mock analyzing image path: {image_path}")
        
        # Mock Claude Vision Analysis
        result = await analyze_image_with_claude_mock(image_path)
        
        if result.get("status") == "completed":
            logger.info("✅ Mock Claude Vision analysis completed successfully")
            return JSONResponse(content={
                "success": True,
                "data": result,
                "message": "Mock Claude Vision analysis completed"
            })
        else:
            logger.error(f"❌ Mock Claude Vision analysis failed: {result.get('error', 'Unknown error')}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": result.get("error", "Analysis failed"),
                    "message": "Mock Claude Vision analysis failed"
                }
            )
            
    except Exception as e:
        logger.error(f"❌ Mock Claude Vision endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/claude/health")
async def claude_health_check() -> JSONResponse:
    """
    Health Check für Mock Claude Vision Service
    """
    return JSONResponse(content={
        "status": "healthy",
        "service": "claude-vision-mock-api",
        "model": "claude-3-5-sonnet-mock",
        "max_megapixels": 5.0
    })

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Claude Vision Mock Service", "status": "running"}

if __name__ == "__main__":
    logger.info("🚀 Starting Claude Vision Mock Service on port 2015...")
    uvicorn.run(
        "claude_mock_service:app",
        host="0.0.0.0",
        port=2015,
        reload=False,
        log_level="info"
    )
