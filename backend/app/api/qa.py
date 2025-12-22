from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel
from app.services import rag_service, tts_service
from app.config import settings
import os
import json

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice_id: str | None = None

@router.post("/tts")
async def tts_endpoint(request: TTSRequest):
    """
    Generate audio from text using MURF.ai
    """
    try:
        audio_bytes = await tts_service.synthesize_async(request.text, request.voice_id)
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    answer: str
    sources: list
    context: list
    language: str

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Text-based query endpoint (fallback for non-voice interactions).
    """
    result = await rag_service.query(request.message)
    
    return QueryResponse(
        answer=result['answer'],
        sources=result['sources'],
        context=result['context'],
        language=result.get('language', 'en-US')
    )

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
