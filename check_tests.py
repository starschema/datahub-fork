#!/usr/bin/env python3
"""Check if Test entities and TestResults exist in DataHub."""
import json
import requests

url = "http://localhost:9002/api/graphql"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhY3RvclR5cGUiOiJVU0VSIiwiYWN0b3JJZCI6ImRhdGFodWIiLCJ0eXBlIjoiUEVSU09OQUwiLCJ2ZXJzaW9uIjoiMiIsImp0aSI6IjdmY2Y2NjcwLTM3YjAtNGRkNy05NjI1LTlmNWQ3MzFhOTg3NCIsInN1YiI6ImRhdGFodWIiLCJleHAiOjE3NjIyODY5MTYsImlzcyI6ImRhdGFodWItbWV0YWRhdGEtc2VydmljZSJ9.ePEOXMq3_VXhGqrF2LIsJiE4NFcPLwJMcP6vk0zCYYw"
}

query = """{
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:postgres,test_db.public.nurses,PROD)") {
    urn
    testResults {
      passing {
        test {
          urn
          info {
            name
            category
          }
        }
        type
      }
      failing {
        test {
          urn
          info {
            name
            category
          }
        }
        type
      }
    }
  }
}"""

response = requests.post(url, json={"query": query}, headers=headers)
result = response.json()

print("=" * 80)
print("GOVERNANCE TEST RESULTS")
print("=" * 80)
print(json.dumps(result, indent=2))

if "data" in result and result["data"]["dataset"]:
    test_results = result["data"]["dataset"]["testResults"]
    if test_results:
        passing = test_results.get("passing", [])
        failing = test_results.get("failing", [])

        print("\n" + "=" * 80)
        print(f"PASSING TESTS: {len(passing)}")
        for test in passing:
            if test.get("test"):
                print(f"  - {test['test'].get('info', {}).get('name', 'Unknown')}")
                print(f"    URN: {test['test'].get('urn')}")
            else:
                print(f"  - Test reference is null")

        print(f"\nFAILING TESTS: {len(failing)}")
        for test in failing:
            if test.get("test"):
                print(f"  - {test['test'].get('info', {}).get('name', 'Unknown')}")
                print(f"    URN: {test['test'].get('urn')}")
            else:
                print(f"  - Test reference is null")

        if not passing and not failing:
            print("\nNo test results found!")
    else:
        print("\ntestResults is null or empty")
else:
    print("\nNo dataset found or error in query")
