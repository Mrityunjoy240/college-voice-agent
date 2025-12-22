import requests
import json

def test_query():
    url = "http://localhost:8000/qa/query"
    # payload = {"message": "Who is the HOD of AIML?"}
    payload = {"message": "What is the fee for B.Tech?"}
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Sending query to {url}...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse:")
            print(json.dumps(data, indent=2))
            
            # if "Gour Sundar Mitra Thakur" in data['answer'] or "Thakur" in data['answer']:
            if "89,650" in data['answer'] or "fee" in data['answer'].lower():
                print("\n✅ SUCCESS: Found Fee info.")
            else:
                print("\n❌ FAILURE: Did not find Fee info.")
        else:
            print(f"\n❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")

if __name__ == "__main__":
    test_query()
