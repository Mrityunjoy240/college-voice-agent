from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Dict
import shutil
import os
import json
from pathlib import Path
import logging

from app.config import settings
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

document_processor = DocumentProcessor(settings.upload_dir)

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload files to the server and process them in the background.
    """
    uploaded_files = []
    
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    for file in files:
        file_path = os.path.join(settings.upload_dir, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file.filename)
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            
    # Trigger processing in background
    if background_tasks:
        background_tasks.add_task(process_and_index_files, uploaded_files)
    
    return {"message": f"Successfully uploaded {len(uploaded_files)} files", "files": uploaded_files}

@router.get("/files")
async def list_files():
    """
    List uploaded files.
    """
    try:
        if not os.path.exists(settings.upload_dir):
            return []
        files = os.listdir(settings.upload_dir)
        return [{"name": f, "size": os.path.getsize(os.path.join(settings.upload_dir, f))} for f in files]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_and_index_files(filenames: List[str]):
    """
    Process uploaded files and update the index.
    """
    all_documents = []
    
    # Load existing documents if any
    storage_file = Path(settings.chroma_persist_dir) / "documents.json"
    
    # Create directory if not exists
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    
    if storage_file.exists():
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                all_documents = json.load(f)
        except Exception as e:
            logger.error(f"Error loading existing documents: {e}")

    # Process new files
    new_docs = []
    for filename in filenames:
        file_path = os.path.join(settings.upload_dir, filename)
        try:
            docs = await document_processor.process_file(file_path)
            new_docs.extend(docs)
            logger.info(f"Processed {filename}: {len(docs)} chunks")
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            
    # Remove old documents from the same source to avoid duplicates
    # (Simple logic: if we re-upload a file, we replace its chunks)
    processed_sources = set(doc['source'] for doc in new_docs)
    all_documents = [doc for doc in all_documents if doc.get('source') not in processed_sources]
    
    # Add new documents
    all_documents.extend(new_docs)
    
    # Save updated documents
    try:
        with open(storage_file, 'w', encoding='utf-8') as f:
            json.dump(all_documents, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(all_documents)} documents to {storage_file}")
        
        # Trigger reload in active services
        qa_rag.reload_documents()
        voice_rag.reload_documents()
        
    except Exception as e:
        logger.error(f"Error saving documents: {e}")
