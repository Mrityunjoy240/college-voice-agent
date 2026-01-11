from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import json
import logging
import os
from pathlib import Path
import time

from app.services.rag import RAGService
from app.config import settings
from app.services.tts import TTSService
from app.services.stt import STTService
from app.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize RAG service
rag_service = RAGService()

# Initialize TTS and STT services
tts_service = TTSService()
stt_service = STTService()

class QueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    session_id: str

class TTSRequest(BaseModel):
    text: str
    session_id: Optional[str] = None

@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query_endpoint(request: Request, query_data: QueryRequest):
    """Handle text-based queries with response caching"""
    start_time = time.time()
    session_id = getattr(request.state, 'session_id', 'default')
    logger.info(f"[{session_id}] Query received: '{query_data.message[:60]}...'")
    try:
        # Check cache first for instant response
        cached_answer = rag_service.response_cache.get(query_data.message)
        if cached_answer:
            logger.info(f"Returning cached response for: {query_data.message[:50]}...")
            session_id = getattr(request.state, 'session_id', 'default')
            return QueryResponse(
                answer=cached_answer,
                sources=[],
                session_id=session_id
            )
        
        # Set clients for RAG service if not already set
        college_config = {
            'name': settings.college_name,
            'admissions_phone': settings.admissions_phone,
            'support_email': settings.support_email
        }
        rag_service.set_clients(settings.groq_client, college_config)
        

        
        # Process the query
        logger.info(f"[{session_id}] Processing query via RAGService...")
        async for result in rag_service.query_stream(query_data.message, query_data.session_id):
            if result["type"] == "answer":
                # Return the generated answer
                answer = result.get("answer", f"I don't have that information. Please contact {settings.college_name} Admissions at {settings.admissions_phone}")
                sources = [doc["document"] for doc in result.get("documents", [])[:3]]  # Top 3
                session_id = query_data.session_id or "default"
                
                # Cache the response for future queries
                # rag_service.response_cache.set(query_data.message, answer) <-- Removed (handled in RAGService)
                

                
                elapsed = time.time() - start_time
                logger.info(f"[{session_id}] Query processed in {elapsed:.2f}s")
                return QueryResponse(
                    answer=answer,
                    sources=sources,
                    session_id=session_id
                )
            elif result["type"] == "error":
                logger.error(f"Error in query processing: {result['message']}")
                return QueryResponse(
                    answer="I'm having trouble processing your request. Please try again.",
                    sources=[],
                    session_id=query_data.session_id or "default"
                )
        
        # Fallback response
        return QueryResponse(
            answer="I'm having trouble processing your request. Please try again.",
            sources=[],
            session_id=query_data.session_id or "default"
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tts")
@limiter.limit("20/minute")
async def tts_endpoint(tts_data: TTSRequest, request: Request):
    """Convert text to speech"""
    try:
        # Use default voice if none provided
        audio_content = await tts_service.text_to_speech(tts_data.text)
        
        # Save to temporary file and return path
        session_id = tts_data.session_id or "default"
        filename = f"tts_{session_id}_{hash(tts_data.text)}.mp3"
        filepath = os.path.join(settings.temp_audio_dir, filename)
        
        os.makedirs(settings.temp_audio_dir, exist_ok=True)
        
        with open(filepath, "wb") as f:
            f.write(audio_content)
        
        return {"audio_url": f"/audio/{filename}", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error in TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    doc_count = rag_service.get_document_count()
    groq_ok = rag_service.check_groq_connection()
    
    return {
        'status': 'healthy' if groq_ok else 'degraded',
        'groq_connected': groq_ok,
        'document_count': doc_count
    }

class FeedbackRequest(BaseModel):
    message: str
    answer: str
    rating: str  # 'up' or 'down'
    comment: str | None = None

class FeedbackResponse(BaseModel):
    status: str
    saved: bool

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """Collect user feedback for continuous improvement."""
    storage_file = os.path.join(settings.chroma_persist_dir, 'feedback.json')
    os.makedirs(os.path.dirname(storage_file), exist_ok=True)
    data = []
    try:
        if os.path.exists(storage_file):
            with open(storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f) or []
    except Exception:
        data = []

    entry = {
        'message': feedback.message,
        'answer': feedback.answer,
        'rating': feedback.rating,
        'comment': feedback.comment or "",
    }
    try:
        data.append(entry)
        with open(storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return FeedbackResponse(status='ok', saved=True)
    except Exception:
        return FeedbackResponse(status='error', saved=False)

# WebSocket for voice interactions
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Check if Groq client is available
    if not settings.groq_client:
        error_msg = f"I'm having trouble connecting to the AI service. Please make sure your GROQ_API_KEY is set in the environment."
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": error_msg
        }))
        await websocket.close()
        return
    
    # Set clients for RAG service
    college_config = {
        'name': settings.college_name,
        'admissions_phone': settings.admissions_phone,
        'support_email': settings.support_email
    }
    rag_service.set_clients(settings.groq_client, college_config)
    
    # Send ready message with session ID
    session_id = f"session_{hash(websocket) % 10000}"
    await websocket.send_text(json.dumps({
        "type": "ready",
        "session_id": session_id
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "transcribe":
                audio_data = message_data.get("audio")
                # Process audio through STT
                transcript = await stt_service.transcribe_audio(audio_data)
                
                if transcript:
                    # Send transcript back
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "text": transcript
                    }))
                    
                    # Process query using RAG
                    async for result in rag_service.query_stream(transcript, session_id):
                        if result["type"] == "answer" and result.get("answer"):
                            answer = result["answer"]
                            
                            # Convert to speech
                            audio_content = await tts_service.text_to_speech(answer)
                            
                            # Send answer to client
                            await websocket.send_text(json.dumps({
                                "type": "answer",
                                "text": answer,
                                "session_id": session_id
                            }))
                            
                            break
                        elif result["type"] == "error":
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": result["message"]
                            }))
                        elif result["type"] == "error":
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": result["message"]
                            }))
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()