import asyncio
import os
import sys
import json
import shutil
from pathlib import Path

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.document_processor import DocumentProcessor
from app.services.vector_store import FAISSVectorStore
from app.config import settings

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def rebuild():
    print("Starting full index rebuild...")
    
    # Paths
    upload_dir = Path("backend/uploads")
    chroma_dir = Path("backend/chroma_db")
    
    # 1. Clean old database
    if chroma_dir.exists():
        print(f"Cleaning {chroma_dir}...")
        try:
            shutil.rmtree(chroma_dir)
        except Exception as e:
            print(f"Error cleaning {chroma_dir}: {e}")
            
    chroma_dir.mkdir(exist_ok=True)
    
    # 2. Process all files
    processor = DocumentProcessor(str(upload_dir))
    files = [f for f in os.listdir(upload_dir) if os.path.isfile(upload_dir / f)]
    
    print(f"Found {len(files)} files to process.")
    
    all_docs = []
    
    for filename in files:
        try:
            print(f"Processing {filename}...")
            file_path = upload_dir / filename
            docs = await processor.process_file(str(file_path))
            all_docs.extend(docs)
            print(f"  -> Generated {len(docs)} chunks")
        except Exception as e:
            import traceback
            print(f"Error processing {filename}: {e}")
            traceback.print_exc()
            
    # 3. Save documents.json
    doc_file = chroma_dir / "documents.json"
    with open(doc_file, 'w', encoding='utf-8') as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_docs)} chunks to {doc_file}")
    
    # 4. Generate Embeddings (Vector Store)
    print("Generating embeddings (this may take a while)...")
    # Note: We use the backend's vector store which we just updated to use all-mpnet-base-v2
    store = FAISSVectorStore(persist_dir=str(chroma_dir), model_name="all-MiniLM-L6-v2")
    store.add_documents(all_docs)
    
    print("Done! Index rebuilt successfully.")

if __name__ == "__main__":
    asyncio.run(rebuild())
