
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_test")

BASE_URL = "http://localhost:8000"

def test_auth():
    print("🔹 Testing Authentication Flow...")
    
    # Can't test "live" against localhost because we aren't starting uvicorn in background here easily without blocking/complex cleanup.
    # But wait, the system prompt says "The actual command will NOT execute until the user approves it... output is captured". 
    # I can try mocking? No, let's assume the user starts the backend.
    # OR better: I can write a unit test style script using FastAPI TestClient! 
    # That works without starting a server!
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # 1. Try to access protected endpoint WITHOUT token
        print("\n1. Accessing /admin/files without token...")
        response = client.get("/admin/files")
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Protected (401 Unauthorized)")
        else:
            print(f"❌ Failed: Expected 401, got {response.status_code}")
            
        # 2. Login to get token
        print("\n2. Logging in...")
        login_data = {"username": "admin", "password": "admin"} # Default credentials
        response = client.post("/token", data=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ Login Successful, Token received")
        else:
            print(f"❌ Login Failed: {response.status_code} {response.text}")
            return

        # 3. Access protected endpoint WITH token
        print("\n3. Accessing /admin/files WITH token...")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/admin/files", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Access Granted (200 OK)")
            print(f"Files: {response.json()}")
        else:
            print(f"❌ Failed: Expected 200, got {response.status_code}")

        # 4. Try Login with WRONG credentials
        print("\n4. Testing Bad Credentials...")
        bad_data = {"username": "admin", "password": "wrongpassword"}
        response = client.post("/token", data=bad_data)
        if response.status_code == 401:
            print("✅ Correctly rejected bad credentials")
        else:
             print(f"❌ Failed: Expected 401, got {response.status_code}")
             
    except ImportError:
        print("❌ httpx/TestClient not installed. Run 'pip install httpx' to test properly.")
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_auth()
