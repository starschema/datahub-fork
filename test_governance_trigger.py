#!/usr/bin/env python3
"""
Trigger governance check by updating dataset metadata.
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

# Dataset URN
dataset_urn = make_dataset_urn(
    platform="postgres",
    name="test_db.public.nurses",
    env="PROD"
)

print(f"Triggering governance check for: {dataset_urn}")

# Add a tag to trigger governance check
tags = GlobalTagsClass(
    tags=[
        TagAssociationClass(tag=make_tag_urn("test-trigger"))
    ]
)

# Emit the change
mcp = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=tags
)

emitter.emit(mcp)
print("✓ Tag added - governance check should trigger")
print("Check container logs with: docker logs datahub-datahub-actions-1 | tail -50")
