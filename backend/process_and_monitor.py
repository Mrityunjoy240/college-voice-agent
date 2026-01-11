
import asyncio
import logging
from app.services.document_processor import DocumentProcessor
from app.services.rag import RAGService
from pathlib import Path
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Initialize services
        doc_processor = DocumentProcessor()
        rag_service = RAGService()
        
        # Get list of files in uploads directory
        uploads_dir = Path("uploads")
        files = [str(f) for f in uploads_dir.iterdir() if f.is_file()]
        
        if not files:
            print("❌ No files found in uploads directory!")
            return

        print(f"found {len(files)} files to process: {files}")
        
        # Process files
        print("Processing files...")
        documents = await doc_processor.process_files_batch(files)
        print(f"✅ Processed into {len(documents)} chunks.")

        # Save documents to JSON (as RAGService expects)
        Path("chroma_db").mkdir(exist_ok=True)
        with open("chroma_db/documents.json", "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2)
            
        # Index documents
        print("Indexing documents into FAISS/BM25...")
        rag_service.hybrid_retriever.index_documents(documents)
        
        print("✅ Indexing Complete!")
        
        # Verify
        print("Running verification query...")
        async for result in rag_service.query_stream("What is the BTech fee?"):
             if result["type"] == "answer":
                 print(f"\nFinal Answer:\n{result['answer']}")
                 print("-" * 50)
                 for doc in result['documents']:
                     print(f"Source: {doc['document'].get('source')} (Score: {doc['hybrid_score']:.2f})")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
