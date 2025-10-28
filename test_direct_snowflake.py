"""Test direct Snowflake connection using the connector, not SQLAlchemy."""
import json
import snowflake.connector
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub_actions.plugin.action.ai_assistant.ingestion_source_client import (
    IngestionSourceClient,
    _resolve_secrets_in_config
)

config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)
client = IngestionSourceClient(graph)

# Get config
sources = client.query_ingestion_sources()
snowflake_source = [s for s in sources if s['type'] == 'snowflake'][0]
recipe = json.loads(snowflake_source['config']['recipe'])
source_config = recipe['source']['config']

# Resolve secrets
resolved = _resolve_secrets_in_config(source_config, graph)

print('=== Resolved Configuration ===')
print(f"account_id: {resolved.get('account_id')}")
print(f"username: {resolved.get('username')}")
print(f"password: [{resolved.get('password')}]")
print(f"warehouse: {resolved.get('warehouse')}")
print(f"role: {resolved.get('role')}")

# Try direct connection (like ingestion does)
print('\\n=== Testing Direct Snowflake Connector ===')
try:
    conn = snowflake.connector.connect(
        user=resolved.get('username'),
        password=resolved.get('password'),
        account=resolved.get('account_id'),
        warehouse=resolved.get('warehouse'),
        role=resolved.get('role'),
        application='acryl_datahub'
    )

    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_VERSION()")
    result = cursor.fetchone()
    print(f'✅ Direct connection SUCCESS: {result[0]}')
    cursor.close()
    conn.close()

except Exception as e:
    print(f'❌ Direct connection FAILED: {e}')

# Try with explicit parameters
print('\\n=== Testing with Explicit Parameters ===')
try:
    conn = snowflake.connector.connect(
        user='DATAHUB_USER',
        password='datahub',
        account='STARSCHEMA-STARSCHEMA',
        warehouse='DATAHUB_WH',
        role='DATAHUB_ROLE',
        application='acryl_datahub'
    )

    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_VERSION()")
    result = cursor.fetchone()
    print(f'✅ Hardcoded connection SUCCESS: {result[0]}')
    cursor.close()
    conn.close()

except Exception as e:
    print(f'❌ Hardcoded connection FAILED: {e}')
