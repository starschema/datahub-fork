import json
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry
from datahub.ingestion.source.sql.snowflake import SnowflakeV2Config
from pydantic import SecretStr
import urllib.parse

config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)
acryl_graph = AcrylDataHubGraph(baseGraph=graph)

# Get the Snowflake source config
sources = acryl_graph.query_ingestion_sources()
snowflake_source = [s for s in sources if s['type'] == 'snowflake'][0]
recipe = json.loads(snowflake_source['config']['recipe'])
source_config = recipe['source']['config']

# Resolve secrets
connector_registry = ConnectorRegistry({}, graph=acryl_graph)
resolved_config = connector_registry._resolve_secrets(source_config)

print('=== Resolved Config ===')
print(f"Username: {resolved_config.get('username')}")
print(f"Password: {resolved_config.get('password')}")
print(f"Account: {resolved_config.get('account_id')}")

# Create SnowflakeV2Config from resolved config
sf_config = SnowflakeV2Config.parse_obj(resolved_config)
generated_url = sf_config.get_sql_alchemy_url()

# Create working hardcoded URL
working_url = 'snowflake://DATAHUB_USER:datahub@STARSCHEMA-STARSCHEMA?application=acryl_datahub&authenticator=SNOWFLAKE&role=DATAHUB_ROLE&warehouse=DATAHUB_WH'

print('\n=== URL Comparison ===')
print(f'Generated URL: {generated_url}')
print(f'Working URL:   {working_url}')

# Parse both URLs to compare components
from urllib.parse import urlparse, parse_qs

gen_parsed = urlparse(generated_url)
work_parsed = urlparse(working_url)

print('\n=== Parsed Components ===')
print(f'Generated - Scheme: {gen_parsed.scheme}')
print(f'Working   - Scheme: {work_parsed.scheme}')
print(f'Generated - Username: {gen_parsed.username}')
print(f'Working   - Username: {work_parsed.username}')
print(f'Generated - Password: [{gen_parsed.password}]')
print(f'Working   - Password: [{work_parsed.password}]')
print(f'Generated - Hostname: {gen_parsed.hostname}')
print(f'Working   - Hostname: {work_parsed.hostname}')
print(f'Generated - Query: {gen_parsed.query}')
print(f'Working   - Query: {work_parsed.query}')

# Check password encoding
print('\n=== Password Hex Comparison ===')
if gen_parsed.password:
    print(f'Generated password hex: {gen_parsed.password.encode().hex()}')
    print(f'Generated password repr: {repr(gen_parsed.password)}')
print(f'Working password hex: {work_parsed.password.encode().hex()}')
print(f'Working password repr: {repr(work_parsed.password)}')

# Check if passwords match
print(f'\nPasswords match: {gen_parsed.password == work_parsed.password}')

# Try manually building URL with SecretStr
print('\n=== Manual URL Building Test ===')
password_value = resolved_config.get('password')
print(f'Password value type: {type(password_value)}')
print(f'Password value: [{password_value}]')

# If it's already a string, use it directly
manual_url = f'snowflake://DATAHUB_USER:{password_value}@STARSCHEMA-STARSCHEMA?application=acryl_datahub&authenticator=SNOWFLAKE&role=DATAHUB_ROLE&warehouse=DATAHUB_WH'
print(f'Manual URL: {manual_url}')

# Test with SQLAlchemy
from sqlalchemy import create_engine
print('\n=== Connection Tests ===')
try:
    engine = create_engine(working_url)
    with engine.connect() as conn:
        result = conn.execute("SELECT CURRENT_VERSION()").fetchone()
        print(f'✅ Working URL connection succeeded: {result[0]}')
except Exception as e:
    print(f'❌ Working URL failed: {e}')

try:
    engine = create_engine(generated_url)
    with engine.connect() as conn:
        result = conn.execute("SELECT CURRENT_VERSION()").fetchone()
        print(f'✅ Generated URL connection succeeded: {result[0]}')
except Exception as e:
    print(f'❌ Generated URL failed: {e}')

try:
    engine = create_engine(manual_url)
    with engine.connect() as conn:
        result = conn.execute("SELECT CURRENT_VERSION()").fetchone()
        print(f'✅ Manual URL connection succeeded: {result[0]}')
except Exception as e:
    print(f'❌ Manual URL failed: {e}')
