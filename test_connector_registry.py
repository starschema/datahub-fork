"""Test connector registry secret resolution."""

import logging
logging.basicConfig(level=logging.DEBUG)

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub_actions.api.action_graph import AcrylDataHubGraph
from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry

# Initialize DataHub connection
config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)
acryl_graph = AcrylDataHubGraph(baseGraph=graph)

# Create connector registry (same as API does)
connector_registry = ConnectorRegistry({}, graph=acryl_graph)

# Test URN
dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,STARSCHEMA-STARSCHEMA.datahub_db.public.lineage_table_1,PROD)"

print("\n=== Testing Connector Registry ===")
try:
    engine = connector_registry.get_engine(dataset_urn)
    if engine:
        print(f"✅ Engine created: {engine.url}")

        # Try a simple query
        with engine.connect() as conn:
            result = conn.execute("SELECT CURRENT_VERSION()")
            version = result.fetchone()[0]
            print(f"✅ Connection successful: {version}")
    else:
        print("❌ No engine returned")
except Exception as e:
    print(f"❌ Failed: {e}")
