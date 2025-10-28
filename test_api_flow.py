"""Test the exact flow the API uses to connect to Snowflake."""

import logging
logging.basicConfig(level=logging.DEBUG)

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub_actions.plugin.action.ai_assistant.executor import SQLExecutor
from datahub_actions.plugin.action.ai_assistant.ingestion_source_client import IngestionSourceClient

# Initialize DataHub connection
config = DatahubClientConfig(server='http://datahub-gms:8080')
graph = DataHubGraph(config=config)

# Initialize ingestion source client
ingestion_client = IngestionSourceClient(graph=graph)

# Initialize SQL executor
executor = SQLExecutor(
    connector_registry=None,
    ingestion_source_client=ingestion_client
)

# Test execution
dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,STARSCHEMA-STARSCHEMA.datahub_db.public.lineage_table_1,PROD)"
sql = "SELECT CURRENT_VERSION()"

print("\\n=== Attempting Query Execution ===")
passed, metrics, error = executor.execute_query(
    dataset_urn=dataset_urn,
    sql=sql,
    timeout_sec=10,
    row_limit=10
)

print(f"\\nPassed: {passed}")
print(f"Metrics: {metrics}")
print(f"Error: {error}")
