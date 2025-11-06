#!/usr/bin/env python3
"""
Trigger governance check for Snowflake dataset by updating metadata.
"""
from datahub.emitter.mce_builder import make_dataset_urn, make_tag_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import GlobalTagsClass, TagAssociationClass

# Create emitter
emitter = DatahubRestEmitter(
    gms_server="http://localhost:8080",
    token="eyJhbGciOiJIUzI1NiJ9.eyJhY3RvclR5cGUiOiJVU0VSIiwiYWN0b3JJZCI6ImRhdGFodWIiLCJ0eXBlIjoiUEVSU09OQUwiLCJ2ZXJzaW9uIjoiMiIsImp0aSI6IjdmY2Y2NjcwLTM3YjAtNGRkNy05NjI1LTlmNWQ3MzFhOTg3NCIsInN1YiI6ImRhdGFodWIiLCJleHAiOjE3NjIyODY5MTYsImlzcyI6ImRhdGFodWItbWV0YWRhdGEtc2VydmljZSJ9.ePEOXMq3_VXhGqrF2LIsJiE4NFcPLwJMcP6vk0zCYYw"
)

# Snowflake Dataset URN
dataset_urn = make_dataset_urn(
    platform="snowflake",
    name="covid19.public.cdc_inpatient_beds_all",
    env="PROD"
)

print(f"Triggering governance check for Snowflake dataset: {dataset_urn}")

# Add a tag to trigger governance check
tags = GlobalTagsClass(
    tags=[
        TagAssociationClass(tag=make_tag_urn("snowflake-governance-test"))
    ]
)

# Emit the change
mcp = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=tags
)

emitter.emit(mcp)
print("✓ Tag added to Snowflake dataset - governance check should trigger")
print("Check logs with: docker logs datahub-datahub-actions-1 --tail 50")
