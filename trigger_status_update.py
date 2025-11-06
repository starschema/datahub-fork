#!/usr/bin/env python3
"""
Trigger governance by updating status aspect (always processed during ingestion).
"""
import requests
import json

GMS_URL = "http://localhost:8888"
SYSTEM_AUTH = "Basic __datahub_system:JohnSnowKnowsNothing"

# Pick a different Snowflake table from the ingestion
dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,safegraph_uscensus_and_neighborhood.public.data_cbg_b01,PROD)"

print(f"Triggering governance via status update: {dataset_urn}")

# Update status aspect (always triggers governance now)
payload = {
    "proposal": {
        "entityType": "dataset",
        "entityUrn": dataset_urn,
        "aspectName": "status",
        "aspect": {
            "contentType": "application/json",
            "value": json.dumps({
                "removed": False
            })
        },
        "changeType": "UPSERT"
    }
}

headers = {
    "Content-Type": "application/json",
    "X-RestLi-Protocol-Version": "2.0.0",
    "Authorization": SYSTEM_AUTH
}

try:
    response = requests.post(
        f"{GMS_URL}/aspects?action=ingestProposal",
        json=payload,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    print(f"Success! Status updated (Code: {response.status_code})")
    print("\nGovernance should trigger in 1-2 seconds for this table.")
    print("Check with:")
    print("  docker logs datahub-datahub-actions-1 --tail 30 | grep -i 'data_cbg_b01'")
except Exception as e:
    print(f"Failed: {e}")
