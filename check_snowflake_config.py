import json
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub_actions.api.action_graph import AcrylDataHubGraph

config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)
acryl_graph = AcrylDataHubGraph(baseGraph=graph)

# Get the Snowflake source config
sources = acryl_graph.query_ingestion_sources()
snowflake_source = [s for s in sources if s['type'] == 'snowflake'][0]
recipe = json.loads(snowflake_source['config']['recipe'])
source_config = recipe['source']['config']

print('=== Snowflake Source Configuration ===')
print(json.dumps(source_config, indent=2))

# Check for specific fields
print('\n=== Key Configuration Fields ===')
print(f"account_id: {source_config.get('account_id')}")
print(f"username: {source_config.get('username')}")
print(f"password: {source_config.get('password')}")
print(f"warehouse: {source_config.get('warehouse')}")
print(f"database: {source_config.get('database')}")
print(f"schema: {source_config.get('schema')}")
print(f"role: {source_config.get('role')}")
print(f"authentication_type: {source_config.get('authentication_type')}")
print(f"host_port: {source_config.get('host_port')}")
print(f"connect_args: {source_config.get('connect_args')}")
