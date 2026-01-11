import requests
import json

# Test the query endpoint
try:
    response = requests.post(
        "http://localhost:8000/qa/query",
        json={"message": "hello"},
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
