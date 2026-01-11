import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.rag import RAGService
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING) # Reduce noise

async def run_test():
    print("Initializing RAG Service...")
    # Mock settings if needed, but they should load from .env or defaults
    rag = RAGService()
    
    questions = [
        "Who is the HOD of CSE?",
        "What is the fee for B.Tech CSE?",
        "Can I get into CSE with rank 5000?"
    ]
    
    print("\n" + "="*50)
    print("VERIFICATION TEST")
    print("="*50)
    
    for q in questions:
        print(f"\nQuestion: {q}")
        print("-" * 20)
        
        # We need to simulate the generator consumption
        response_text = ""
        docs = []
        async for result in rag.query_stream(q, "test_session"):
            if result["type"] == "answer":
                response_text = result["answer"]
                docs = result["documents"]
                
        print(f"Answer: {response_text}")
        print("\nRetrieved Sources:")
        for i, doc in enumerate(docs[:3]):
            source = doc['document'].get('source', 'Unknown')
            score = doc['hybrid_score']
            content = doc['document'].get('text', '')[:100].replace('\n', ' ')
            print(f"  {i+1}. [{source}] (Score: {score:.4f}) - {content}...")
            
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(run_test())
