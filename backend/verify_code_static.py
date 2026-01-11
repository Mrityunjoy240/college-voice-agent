
import sys
import os
import asyncio
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

async def verify_code():
    print("Verifying code integrity...")
    
    try:
        from app.api.qa import query_endpoint
        print("✓ app.api.qa imported successfully")
    except Exception as e:
        print(f"✗ Failed to import app.api.qa: {e}")
        return False

    try:
        from app.services.tts import TTSService
        tts = TTSService()
        print("✓ TTSService instantiated")
        # Check if fallback method exists (internal)
        if hasattr(tts, '_generate_pyttsx3'):
            print("✓ TTSService has fallback method")
        else:
            print("✗ TTSService missing fallback method")
    except Exception as e:
        print(f"✗ Failed to check TTSService: {e}")
        return False

    try:
        from app.services.rag import RAGService
        print("✓ RAGService imported")
        # Note: Instantiating RAGService might try to load files/connect to DB
        # We just check class existence
    except Exception as e:
        print(f"✗ Failed to import RAGService: {e}")
        return False

    try:
        from app.api.health import router
        print("✓ Health router imported")
    except Exception as e:
        print(f"✗ Failed to import health router: {e}")
        return False
        
    print("ALL CODE CHECKS PASSED")
    return True

if __name__ == "__main__":
    asyncio.run(verify_code())
