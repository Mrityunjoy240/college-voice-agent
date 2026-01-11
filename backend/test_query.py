
import asyncio
import logging
import os
from app.config import settings
from app.services.rag import RAGService
from groq import Groq

# Setup
logging.basicConfig(level=logging.ERROR) # Only show errors
logger = logging.getLogger(__name__)

# Ensure API key is loaded
if not settings.groq_api_key:
    print("❌ Error: GROQ_API_KEY is missing!")
    exit(1)

# Initialize Groq Client manually (because config.py might have loaded before env var was set if not careful, though it should be fine)
# But let's rely on settings.
client = Groq(api_key=settings.groq_api_key)

async def test_query():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    # Inject client and config (normally happen in API endpoint)
    college_config = {
        'name': 'Dr. B.C. Roy Engineering College',
        'admissions_phone': '+91-343-2567890',
        'support_email': 'admissions@bcrec.ac.in'
    }
    rag.set_clients(client, college_config=college_config)
    
    # Query 1: Fees
    query1 = "What is the B.Tech tuition fee per semester?"
    print(f"\n🔹 Query: {query1}")
    async for result in rag.query_stream(query1):
        if result['type'] == 'answer':
            print(f"✅ Answer: {result['answer']}")
            
    # Query 2: Courses
    query2 = "What courses are offered in Computer Science?"
    print(f"\n🔹 Query: {query2}")
    async for result in rag.query_stream(query2):
        if result['type'] == 'answer':
            print(f"✅ Answer: {result['answer']}")

if __name__ == "__main__":
    asyncio.run(test_query())
