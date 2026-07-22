"""
FastAPI Server for Audio Customer Support Agent

This module provides REST API endpoints for testing the audio support pipeline.
Students can use this server to test their implementations via HTTP requests.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import logging
import os
import base64
from dotenv import load_dotenv

from src.pipeline import AudioSupportPipeline, create_pipeline, create_pipeline, PipelineConfig

load_dotenv()
class TextRequest(BaseModel):
    """Request model for text-based queries."""
    text: str
    parameters: Optional[Dict[str, Any]] = {}


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    components: Dict[str, bool]
    message: str




class TranscriptData(BaseModel):
    user_input: str
    agent_response: str


class EnhancedAudioResponse(BaseModel):
    success: bool
    audio_response: str
    transcript: TranscriptData
    response_text: str
    processing_time_ms: int


class TextResponse(BaseModel):
    """Response model for text queries."""
    response_text: str
    audio_available: bool
    processing_time_ms: int


app = FastAPI(
    title="Audio Customer Support Agent API",
    description="REST API for testing the STT -> LLM -> TTS pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline: Optional[AudioSupportPipeline] = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """
    TODO: Initialize the pipeline on server startup.
    
    Students should configure the pipeline with their API keys and settings.
    """
    global pipeline
    
    try:
        logger.info("Starting Audio Support Agent API server...")
        
        # TODO: Configure your chosen services
        # Replace these configurations with your implementation choices
        
        stt_config = {
            "provider": os.getenv("STT_PROVIDER", "whisper"),
            "api_key": os.getenv("STT_API_KEY") or os.getenv("DEEPGRAM_API_KEY"),
            "model": os.getenv("STT_MODEL", "tiny"),
        }
        
        llm_config = {
            "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"),
            "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        }
        
        tts_config = {
            "provider": os.getenv("TTS_PROVIDER", "edge"),
            "api_key": os.getenv("TTS_API_KEY") or os.getenv("ELEVENLABS_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "voice": os.getenv("TTS_VOICE", "en-US-AriaNeural"),
            "voice_id": os.getenv("ELEVENLABS_VOICE_ID", "en-US-AriaNeural"),
            "model": os.getenv("TTS_MODEL", "tts-1"),
        }
        
        pipeline = await create_pipeline(stt_config, llm_config, tts_config)
        logger.info("Pipeline initialized successfully.")
        
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {str(e)}")
        # Don't raise here to allow server to start for debugging


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup pipeline resources on server shutdown."""
    global pipeline
    
    if pipeline:
        logger.info("Shutting down pipeline...")
        await pipeline.cleanup()
        pipeline = None


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Audio Customer Support Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns the status of all pipeline components.
    """
    global pipeline
    
    if not pipeline:
        return HealthResponse(
            status="unhealthy",
            components={
                "pipeline_initialized": False,
                "stt_ready": False,
                "llm_ready": False,
                "tts_ready": False
            },
            message="Pipeline not initialized"
        )
    
    try:
        components = await pipeline.health_check()
        
        all_healthy = all(components.values())
        
        return HealthResponse(
            status="healthy" if all_healthy else "unhealthy",
            components=components,
            message="All components ready" if all_healthy else "Some components not ready"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="error",
            components={},
            message=f"Health check failed: {str(e)}"
        )


@app.post("/chat/text", response_model=TextResponse)
async def chat_text(request: TextRequest):
    """
    Process text query through the LLM agent.
    
    This endpoint allows testing the LLM component without audio processing.
    """
    global pipeline
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        import time
        start_time = time.time()
        
        response_text, response_audio = await pipeline.process_text(
            request.text,
            **request.parameters
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return TextResponse(
            response_text=response_text,
            audio_available=bool(response_audio),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Text processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/audio", response_model=EnhancedAudioResponse)
async def audio_chat(audio: UploadFile = File(...)):
    global pipeline

    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        response_audio, transcript_data, processing_time = await pipeline.process_audio_with_transcript(audio_bytes)

        encoded_audio = base64.b64encode(response_audio).decode("utf-8")

        return {
            "success": True,
            "audio_response": encoded_audio,
            "transcript": transcript_data,
            "response_text": transcript_data.get("agent_response", ""),
            "processing_time_ms": processing_time
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/audio/{text}")
async def text_to_audio(text: str):
    """
    TODO: Convert text to audio using TTS.
    
    Useful for testing TTS component independently.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        Audio file as bytes
    """
    global pipeline
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        if not pipeline.tts:
            raise HTTPException(status_code=503, detail="TTS not available")

        audio_bytes = await pipeline.tts.synthesize(text)
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=tts_output.mp3"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/stt")
async def debug_stt(audio: UploadFile = File(...)):
    """
    TODO: Debug endpoint for testing STT component independently.
    
    Args:
        audio: Audio file to transcribe
        
    Returns:
        Transcription result
    """
    global pipeline
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        audio_bytes = await audio.read()
        
        if not pipeline.stt:
            raise HTTPException(status_code=503, detail="STT not available")

        transcription = await pipeline.stt.transcribe(audio_bytes)
        
        return {"transcription": transcription}
        
    except Exception as e:
        logger.error(f"STT debug failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # TODO: Students can modify these settings for development
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )