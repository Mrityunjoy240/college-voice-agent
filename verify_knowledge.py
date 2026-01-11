import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.rag import RAGService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_knowledge():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    test_queries = [
        "What is the fee structure?",
        "List all courses offered.",
        "What is the intake for CSE?"
    ]
    
    print("\n" + "="*50)
    print("PHASE 2 VERIFICATION: KNOWLEDGE GRAPH")
    print("="*50)
    
    for q in test_queries:
        print(f"\nQuery: {q}")
        print("-" * 20)
        
        async for result in rag.query_stream(q, "test_session"):
            if result["type"] == "answer":
                print(f"Answer:\n{result['answer']}")
                
                # Check if it came from deterministic source (implied by content)
                if "**Official Fee Structure:**" in result['answer'] or "**Courses Offered:**" in result['answer']:
                     print("\n[SUCCESS] Answer came from Knowledge Graph ✅")
                else:
                     print("\n[WARNING] Answer might be from Vector Search (Hybrid) ⚠️")
            
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(test_knowledge())
