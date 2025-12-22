from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.services import rag_service, doc_processor
from app.services.document_processor import DocumentProcessor
from app.config import settings
import os
import shutil
from typing import List
from pydantic import BaseModel

router = APIRouter()

class FileInfo(BaseModel):
    filename: str
    size: int
    uploaded_at: str
    processing_status: str = "uploaded"  # uploaded, processing, completed, failed
    chunks_processed: int = 0
    total_chunks: int = 0

class UploadResponse(BaseModel):
    message: str
    filename: str
    status: str
    processing_status: str = "uploaded"

def process_uploaded_file(file_path: str, filename: str):
    """Background task to process uploaded file."""
    # Update status file to indicate processing started
    status_file = os.path.join(settings.upload_dir, f"{filename}.status")
    try:
        # Mark as processing
        with open(status_file, 'w') as f:
            json.dump({
                "status": "processing",
                "chunks_processed": 0,
                "total_chunks": 0
            }, f)
        
        # Process document
        chunks = doc_processor.process_file(file_path)
        
        # Update status with total chunks
        with open(status_file, 'w') as f:
            json.dump({
                "status": "processing",
                "chunks_processed": 0,
                "total_chunks": len(chunks)
            }, f)
        
        # Add to RAG system
        rag_service.add_documents(chunks)
        
        # Mark as completed
        with open(status_file, 'w') as f:
            json.dump({
                "status": "completed",
                "chunks_processed": len(chunks),
                "total_chunks": len(chunks)
            }, f)
        
        print(f"Successfully processed {filename}: {len(chunks)} chunks")
    
    except Exception as e:
        # Mark as failed
        try:
            with open(status_file, 'w') as f:
                json.dump({
                    "status": "failed",
                    "error": str(e)
                }, f)
        except:
            pass
        print(f"Error processing {filename}: {str(e)}")

@router.post("/files/", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and process a document file.
    Supported formats: PDF, Excel, CSV, TXT
    """
    # Validate file type
    allowed_extensions = {'.pdf', '.xlsx', '.xls', '.csv', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save file
    file_path = os.path.join(settings.upload_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Process in background
    background_tasks.add_task(process_uploaded_file, file_path, file.filename)
    
    return UploadResponse(
        message="File uploaded successfully and is being processed",
        filename=file.filename,
        status="processing"
    )

@router.get("/files/", response_model=List[FileInfo])
async def list_files():
    """List all uploaded files with processing status."""
    files = []
    
    if os.path.exists(settings.upload_dir):
        for filename in os.listdir(settings.upload_dir):
            # Skip status files
            if filename.endswith('.status'):
                continue
                
            file_path = os.path.join(settings.upload_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                
                # Check for status file
                status_file = os.path.join(settings.upload_dir, f"{filename}.status")
                processing_status = "uploaded"
                chunks_processed = 0
                total_chunks = 0
                
                if os.path.exists(status_file):
                    try:
                        with open(status_file, 'r') as f:
                            status_data = json.load(f)
                            processing_status = status_data.get("status", "uploaded")
                            chunks_processed = status_data.get("chunks_processed", 0)
                            total_chunks = status_data.get("total_chunks", 0)
                    except:
                        pass
                
                files.append(FileInfo(
                    filename=filename,
                    size=stat.st_size,
                    uploaded_at=str(stat.st_mtime),
                    processing_status=processing_status,
                    chunks_processed=chunks_processed,
                    total_chunks=total_chunks
                ))
    
    return files

@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    Delete an uploaded file and remove its data from the knowledge base.
    This removes both the file from disk and all associated chunks from the RAG system.
    """
    file_path = os.path.join(settings.upload_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Remove file from disk
        os.remove(file_path)
        
        # Remove all document chunks associated with this file from the knowledge base
        deleted_chunks = rag_service.delete_documents_by_source(filename)
        
        return {
            "message": f"File {filename} deleted successfully",
            "deleted_chunks": deleted_chunks,
            "status": "deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@router.post("/rebuild-embeddings/")
async def rebuild_embeddings(background_tasks: BackgroundTasks):
    """
    Rebuild all embeddings from uploaded files.
    Warning: This deletes existing embeddings.
    """
    def rebuild_task():
        try:
            # Clear existing embeddings
            rag_service.delete_all_documents()
            
            # Reprocess all files
            if os.path.exists(settings.upload_dir):
                for filename in os.listdir(settings.upload_dir):
                    file_path = os.path.join(settings.upload_dir, filename)
                    if os.path.isfile(file_path):
                        process_uploaded_file(file_path, filename)
            
            print("Embeddings rebuilt successfully")
        
        except Exception as e:
            print(f"Error rebuilding embeddings: {str(e)}")
    
    background_tasks.add_task(rebuild_task)
    
    return {
        "message": "Rebuilding embeddings in background",
        "status": "processing"
    }

@router.get("/stats/")
async def get_stats():
    """Get system statistics."""
    doc_count = rag_service.get_document_count()
    
    file_count = 0
    total_size = 0
    if os.path.exists(settings.upload_dir):
        for filename in os.listdir(settings.upload_dir):
            file_path = os.path.join(settings.upload_dir, filename)
            if os.path.isfile(file_path):
                file_count += 1
                total_size += os.path.getsize(file_path)
    
    return {
        "total_files": file_count,
        "total_size_bytes": total_size,
        "total_chunks": doc_count,
        "groq_connected": rag_service.check_groq_connection()
    }
