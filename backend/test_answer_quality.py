import requests
import json
import time

# Test queries to evaluate answer quality improvements
test_queries = [
    "What is the BTech fee?",
    "What documents do I need for admission?",
    "Tell me about the CSE department",
    "What are the hostel facilities?",
    "When is the admission deadline?"
]

print("=" * 60)
print("TESTING ANSWER QUALITY IMPROVEMENTS")
print("=" * 60)

for i, query in enumerate(test_queries, 1):
    print(f"\n[Test {i}/{len(test_queries)}] Query: {query}")
    print("-" * 60)
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/qa/query",
            json={"message": query},
            timeout=30
        )
        latency = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: Success ({latency:.2f}s)")
            print(f"\nAnswer:\n{data['answer']}\n")
            print(f"Sources: {len(data.get('sources', []))} documents")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(1)  # Rate limiting

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
