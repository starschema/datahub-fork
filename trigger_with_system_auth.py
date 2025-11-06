#!/usr/bin/env python3
"""
Trigger governance check using system authentication.
"""
import requests
import json

# System credentials
GMS_URL = "http://localhost:8888"
SYSTEM_AUTH = "Basic __datahub_system:JohnSnowKnowsNothing"

# Snowflake dataset URN
dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.cdc_inpatient_beds_all,PROD)"

print(f"Triggering governance check for: {dataset_urn}")

# Update dataset description via REST API
payload = {
    "proposal": {
        "entityType": "dataset",
        "entityUrn": dataset_urn,
        "aspectName": "editableDatasetProperties",
        "aspect": {
            "contentType": "application/json",
            "value": json.dumps({
                "description": "COVID-19 inpatient beds data - Governance test update"
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
    print(f"Success! Dataset updated (Status: {response.status_code})")
    print("\nGovernance check should trigger in 1-2 seconds.")
    print("Check logs with:")
    print("  docker logs datahub-datahub-actions-1 --tail 50 | grep -i 'Processing entity\\|governance\\|Successfully emitted'")
except requests.exceptions.HTTPError as e:
    print(f"Failed: {e}")
    print(f"Response: {e.response.text if e.response else 'No response'}")
except Exception as e:
    print(f"Error: {e}")
