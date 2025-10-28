import json
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry

config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)
acryl_graph = AcrylDataHubGraph(baseGraph=graph)

# Get the Snowflake source config
sources = acryl_graph.query_ingestion_sources()
snowflake_source = [s for s in sources if s['type'] == 'snowflake'][0]
recipe = json.loads(snowflake_source['config']['recipe'])
source_config = recipe['source']['config']

print('\n=== Before Secret Resolution ===')
print(f'Password in config: {source_config.get("password")}')

# Create a connector registry and use its secret resolution
connector_registry = ConnectorRegistry({}, graph=acryl_graph)
resolved_config = connector_registry._resolve_secrets(source_config)

print('\n=== After Secret Resolution ===')
pwd = resolved_config.get('password')
if pwd:
    if pwd.startswith('$'):
        print(f'❌ Password was NOT resolved: {pwd}')
    else:
        print(f'✅ Password was resolved: {pwd[:3]}... (length: {len(pwd)} chars)')
else:
    print('❌ Password is missing!')
