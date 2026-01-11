
import logging
from app.services.rag import HybridRetriever

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

try:
    print("Initialize HybridRetriever...")
    retriever = HybridRetriever()
    
    docs = [
        {"text": "The computer science department is located in the main "},
        {"text": "The electronics department is in the new building."},
        {"text": "Admissions are open until July 31st."},
        {"text": "Library is open 24/7 for students."}
    ]
    
    print("Indexing documents...")
    retriever.index_documents(docs)
    
    query = "Where is CS department?"
    print(f"Testing retrieval for: '{query}'")
    results = retriever.retrieve(query, k=1)
    
    if results:
        print(f"✅ Top Result: {results[0]['document']['text']}")
        print(f"   Score: {results[0]['hybrid_score']:.4f}")
    else:
        print("❌ No results found")

except Exception as e:
    print(f"❌ Error during verification: {e}")
    import traceback
    traceback.print_exc()
