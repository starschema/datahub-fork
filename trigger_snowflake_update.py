#!/usr/bin/env python3
"""
Trigger governance check for Snowflake dataset by updating editable properties.
Uses system authentication (no token required).
"""
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import EditableDatasetPropertiesClass
import time

# Create emitter without token (will use system auth from env if available)
emitter = DatahubRestEmitter(
    gms_server="http://localhost:8888",
)

# Snowflake Dataset URN
dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.cdc_inpatient_beds_all,PROD)"

print(f"Updating Snowflake dataset to trigger governance: {dataset_urn}")

# Update editable properties to trigger governance check
editable_properties = EditableDatasetPropertiesClass(
    description=f"COVID-19 inpatient beds data - Updated at {time.strftime('%Y-%m-%d %H:%M:%S')} to trigger governance check"
)

# Emit the change
mcp = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=editable_properties
)

try:
    emitter.emit(mcp)
    print("✓ Dataset updated successfully")
    print("✓ Governance check should trigger in DataHub Actions")
    print("\nCheck logs with:")
    print("  docker logs datahub-datahub-actions-1 --tail 50 | grep -i governance")
    print("\nWait 5-10 seconds, then check the UI:")
    print("  http://localhost:9002")
except Exception as e:
    print(f"✗ Failed to update dataset: {e}")
    print("\nThis might be due to authentication. Checking...")
