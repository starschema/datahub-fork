import requests
import json

# Test the AI Assistant API
api_url = "http://localhost:8082"

# First, test the health endpoint
print("=== Testing Health Endpoint ===")
try:
    response = requests.get(f"{api_url}/healthz", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test executing a query
print("\n=== Testing Query Execution ===")

# Use a simple Snowflake dataset URN (we need to get this from DataHub)
# For now, let's try a test query
test_payload = {
    "dataset_urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,STARSCHEMA-STARSCHEMA.datahub_db.public.lineage_table_1,PROD)",
    "sql": "SELECT CURRENT_VERSION()",
    "config": {
        "type": "test",
        "params": {}
    }
}

print(f"Request payload: {json.dumps(test_payload, indent=2)}")

try:
    response = requests.post(f"{api_url}/execute", json=test_payload, timeout=30)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
