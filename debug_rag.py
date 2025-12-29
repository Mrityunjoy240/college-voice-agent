import asyncio
import os
import sys
import json

# Setup python path to find backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.rag import RAGService
from app.config import settings

# Override storage path for debug script
settings.chroma_persist_dir = os.path.join(os.path.dirname(__file__), 'backend', 'chroma_db')

async def debug_rag_scoring():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    query = "What is the fee for B.Tech?"
    print(f"\nAnalyzing scores for query: '{query}'")
    
    # 1. Expand query to see what synonyms are used
    expanded = rag._expand_query(query)
    print(f"Expanded keywords: {expanded}")
    
    all_queries = [query] + expanded
    
    scores = []
    print(f"Total documents: {len(rag.documents)}")
    
    for i, doc in enumerate(rag.documents):
        total_score = 0
        doc_text = doc['text']
        source = doc.get('metadata', {}).get('source', 'Unknown')
        
        # Simulate the scoring logic in query_stream
        
        # Score original query (High weight)
        total_score += rag._calculate_relevance_score(query, doc_text, weight=1.0)
        
        # Score expanded queries (Lower weight)
        for q in expanded:
            total_score += rag._calculate_relevance_score(q, doc_text, weight=0.25)
            
        if total_score > 0:
            scores.append({
                "source": source,
                "text_preview": doc_text[:50] + "...",
                "score": total_score,
                "chunk_id": doc.get('chunk_id')
            })

    # Sort and show top 10
    scores.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nTop 10 Scored Documents:")
    for i, item in enumerate(scores[:10]):
        print(f"{i+1}. [{item['score']:.2f}] {item['source']} (ID: {item['chunk_id']})")
        print(f"   Preview: {item['text_preview']}")
        
    # Check specifically for the text file
    print("\n--- Check for New Text Document (2).txt ---")
    found = False
    for item in scores:
        if "New Text Document (2).txt" in item['source']:
            print(f"Found: [{item['score']:.2f}] ID: {item['chunk_id']}")
            print(f"Preview: {item['text_preview']}")
            found = True
            
    if not found:
        print("New Text Document (2).txt had 0 score!")

if __name__ == "__main__":
    asyncio.run(debug_rag_scoring())
