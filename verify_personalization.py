import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.rag import RAGService
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)

async def test_personalization():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    # Mock Config for SystemPromptBuilder since it's normally set by main.py
    rag.set_clients(
        llm_client=None, # Mock or handled safely if None
        college_config={
            "name": "Dr. B.C. Roy Engineering College",
            "support_email": "info@bcrec.ac.in",
            "admissions_phone": "1234567890",
            "departments": ["CSE", "IT", "ECE"]
        }
    )
    
    # Needs LLM to actually behave differently, so we check if LLM is set up. 
    # Since we can't easily mock the OpenAI/Groq client here without keys in env,
    # and we know the implementation logic passes the profile to the prompt string,
    # we can verify the PROMPT construction if we could access it.
    
    # Ideally, we run a reliable test. For now, we simulate the profile update memory side.
    
    session_id = "test_user_p3"
    
    print("\n" + "="*50)
    print("PHASE 3 VERIFICATION: PERSONALIZATION")
    print("="*50)

    # 1. Simulate User providing info
    print(f"User: My WBJEE rank is 1500 and I love coding.")
    # We manually update memory because RAGService update logic happens INSIDE query_stream
    rag.conversation_memory.update_user_profile(session_id, "wbjee_rank", "1500")
    rag.conversation_memory.update_user_profile(session_id, "interests", "coding")
    
    print("Memory Updated:")
    print(rag.conversation_memory.get_user_profile(session_id))
    
    # 2. Check Retrieval & Prompt Building
    query = "What branch is best for me?"
    print(f"\nUser Query: {query}")
    
    retrieved_docs = rag.hybrid_retriever.retrieve(query)
    user_profile = rag.conversation_memory.get_user_profile(session_id)
    
    prompt = rag.system_prompt_builder.build_system_prompt(retrieved_docs, user_profile)
    
    if "<user_context>" in prompt and "User Rank: 1500" in prompt:
        print("\n[SUCCESS] User Profile successfully injected into System Prompt! ✅")
        print("Prompt Excerpt:")
        start = prompt.find("<user_context>")
        end = prompt.find("</user_context>") + 15
        print(prompt[start:end])
    else:
        print("\n[FAILURE] User Profile NOT found in System Prompt. ❌")
        
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(test_personalization())
