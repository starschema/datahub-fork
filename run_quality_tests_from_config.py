"""
Run Data Quality Tests from Configuration File

This script:
1. Loads the data-quality-action-config.yaml configuration
2. Searches for all Snowflake datasets in DataHub
3. Runs quality tests on matching datasets
4. Emits assertions to DataHub
"""

import yaml
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub.metadata.schema_classes import EntityChangeEventClass, AuditStampClass
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import EntityChangeEvent
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.data_quality.action import DataQualityAction


def main():
    """Run quality tests from config file on all Snowflake datasets"""

    # Load configuration
    print("Loading data quality configuration...")
    with open("data-quality-action-config.yaml", "r") as f:
        config_yaml = yaml.safe_load(f)

    action_config = config_yaml["action"]["config"]
    print(f"[OK] Loaded {len(action_config['tests'])} quality tests")

    # Connect to DataHub
    print("\nConnecting to DataHub...")
    datahub_config = DatahubClientConfig(server="http://localhost:8888")
    graph = DataHubGraph(datahub_config)
    print("[OK] Connected to DataHub")

    # Search for Snowflake datasets
    print("\nSearching for Snowflake datasets...")
    search_query = """
    {
        search(input: {
            type: DATASET,
            query: "*",
            start: 0,
            count: 100
        }) {
            total
            searchResults {
                entity {
                    urn
                }
            }
        }
    }
    """

    result = graph.execute_graphql(search_query)
    datasets = result.get("search", {}).get("searchResults", [])
    total = result.get("search", {}).get("total", 0)

    print(f"[OK] Found {total} Snowflake datasets")

    if not datasets:
        print("[WARN] No Snowflake datasets found. Have you run ingestion with profiling enabled?")
        return

    # Create pipeline context
    ctx = PipelineContext(pipeline_name="manual-data-quality", graph=graph)

    # Create the data quality action
    action = DataQualityAction.create(action_config, ctx)

    # Process each dataset
    print(f"\nProcessing {len(datasets)} datasets...")
    success_count = 0
    error_count = 0

    for idx, dataset_result in enumerate(datasets, 1):
        dataset_entity = dataset_result.get("entity", {})
        dataset_urn = dataset_entity.get("urn")
        # Extract name from URN (last part after comma)
        dataset_name = dataset_urn.split(",")[-1].rstrip(")") if dataset_urn else "unknown"

        print(f"\n[{idx}/{len(datasets)}] Processing: {dataset_name}")
        print(f"  URN: {dataset_urn}")

        try:
            # Create dataset change event
            entity_change = EntityChangeEvent.from_class(
                EntityChangeEventClass(
                    "dataset",
                    dataset_urn,
                    "MODIFY",
                    "UPDATE",
                    AuditStampClass(0, "urn:li:corpuser:datahub"),
                    0,
                    None,
                    None,
                )
            )

            event_env = EventEnvelope("EntityChangeEvent_v1", entity_change, {})

            # Run tests
            action.act(event_env)
            print(f"  [OK] Tests completed")
            success_count += 1

        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total datasets processed: {len(datasets)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print("\nCheck DataHub UI at http://localhost:9002")
    print("Navigate to any dataset and check the 'Validations' tab")
    print("=" * 60)


if __name__ == "__main__":
    main()
