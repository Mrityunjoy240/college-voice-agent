import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health...")
    try:
        res = requests.get(f"{BASE_URL}/health")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        if res.status_code == 200:
            print("✅ Health Check Passed")
            return True
        else:
            print("❌ Health Check Failed")
            return False
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False

def test_query():
    print("\nTesting /qa/query (Text)...")
    try:
        res = requests.post(
            f"{BASE_URL}/qa/query",
            json={"message": "What is the BTech fee?"},
            timeout=30
        )
        data = res.json()
        print(f"Answer: {data.get('answer')}")
        
        # Check for NO asterisks (Strict formatting check)
        if "**" in data.get('answer', ''):
            print("❌ Formatting Check Failed (Contains markdown)")
        else:
            print("✅ Formatting Check Passed (Clean text)")
            
        if res.status_code == 200:
            print("✅ Query Passed")
            return True
        else:
            print("❌ Query Failed")
            return False
    except Exception as e:
        print(f"❌ Query Test Error: {e}")
        return False

def test_tts():
    print("\nTesting /qa/tts (Voice)...")
    try:
        res = requests.post(
            f"{BASE_URL}/qa/tts",
            json={"text": "Hello, this is a test of the Indian accent voice."}
        )
        data = res.json()
        audio_url = data.get('audio_url')
        print(f"Audio URL: {audio_url}")
        
        if audio_url:
            # Test static file serving
            static_res = requests.get(f"{BASE_URL}{audio_url}")
            if static_res.status_code == 200:
                print(f"✅ Text-to-Speech & Static Serving Passed ({len(static_res.content)} bytes)")
                return True
            else:
                print(f"❌ Static File Serving Failed (Status: {static_res.status_code})")
                return False
        else:
            print("❌ TTS Failed (No URL returned)")
            return False
    except Exception as e:
        print(f"❌ TTS Test Error: {e}")
        return False

if __name__ == "__main__":
    tests = [test_health, test_query, test_tts]
    passed = 0
    for test in tests:
        if test():
            passed += 1
            
    print(f"\nSummary: {passed}/{len(tests)} Tests Passed")
    if passed == len(tests):
        print("🚀 System is Ready for Demo!")
    else:
        print("⚠️ System has issues.")
