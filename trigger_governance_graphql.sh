#!/bin/bash
# Trigger governance check by updating a Snowflake dataset description

DATASET_URN="urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.cdc_inpatient_beds_all,PROD)"
TOKEN="eyJhbGciOiJIUzI1NiJ9.eyJhY3RvclR5cGUiOiJVU0VSIiwiYWN0b3JJZCI6ImRhdGFodWIiLCJ0eXBlIjoiUEVSU09OQUwiLCJ2ZXJzaW9uIjoiMiIsImp0aSI6IjdmY2Y2NjcwLTM3YjAtNGRkNy05NjI1LTlmNWQ3MzFhOTg3NCIsInN1YiI6ImRhdGFodWIiLCJleHAiOjE3NjIyODY5MTYsImlzcyI6ImRhdGFodWItbWV0YWRhdGEtc2VydmljZSJ9.ePEOXMq3_VXhGqrF2LIsJiE4NFcPLwJMcP6vk0zCYYw"

curl -X POST http://localhost:8080/api/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "mutation updateDataset($urn: String!, $input: EditableDatasetPropertiesUpdateInput!) { updateDataset(urn: $urn, input: $input) }",
    "variables": {
      "urn": "'"$DATASET_URN"'",
      "input": {
        "description": "COVID-19 inpatient beds data - Updated to trigger governance check"
      }
    }
  }'

echo ""
echo "✓ Dataset description updated - check governance logs:"
echo "docker logs datahub-datahub-actions-1 --tail 50 | grep governance"
