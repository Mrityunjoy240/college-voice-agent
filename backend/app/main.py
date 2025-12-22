from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import voice, qa, admin
from app.services import rag_service
from app.services.document_processor import DocumentProcessor
import asyncio
import os

# Create FastAPI app
app = FastAPI(
    title="College Info Voice Agent",
    description="RAG-based voice assistant for college information",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router, tags=["Voice"])
app.include_router(qa.router, prefix="/qa", tags=["Q&A"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

async def _index_existing_uploads():
    upload_dir = settings.upload_dir
    if not os.path.exists(upload_dir):
        return

    filenames = [
        name
        for name in os.listdir(upload_dir)
        if os.path.isfile(os.path.join(upload_dir, name))
    ]
    if not filenames:
        return

    processor = DocumentProcessor()
    for filename in sorted(filenames):
        file_path = os.path.join(upload_dir, filename)
        try:
            chunks = await asyncio.to_thread(processor.process_file, file_path)
            rag_service.add_documents(chunks)
        except Exception as e:
            print(f"Error indexing {filename}: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("=" * 50)
    print("Starting College Info Voice Agent...")
    print("Using Groq API (super fast responses!)")
    print("=" * 50)
    print(f"Chroma DB: {settings.chroma_persist_dir}")
    print(f"Upload directory: {settings.upload_dir}")
    
    # Check Groq connection
    if rag_service.check_groq_connection():
        print("[OK] Groq API connected successfully")
    else:
        print("[WARNING] Groq API not connected - check your API key")
    print("=" * 50)

    if rag_service.get_document_count() == 0 and os.path.exists(settings.upload_dir):
        has_files = any(
            os.path.isfile(os.path.join(settings.upload_dir, name))
            for name in os.listdir(settings.upload_dir)
        )
        if has_files:
            asyncio.create_task(_index_existing_uploads())

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "College Info Voice Agent API",
        "version": "1.0.0",
        "endpoints": {
            "voice": "/ws/voice",
            "text_query": "/qa/query",
            "admin": "/admin/files/",
            "health": "/qa/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
