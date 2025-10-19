"""
Test script for Great Expectations Data Quality Integration

This script tests the data quality action locally by:
1. Retrieving profile data from DataHub for a Snowflake dataset
2. Running quality tests against the profile
3. Emitting assertion results to DataHub
"""

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub.metadata.schema_classes import DatasetProfileClass, EntityChangeEventClass, AuditStampClass
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import EntityChangeEvent
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.data_quality.action import DataQualityAction


def main():
    """Test the data quality integration"""

    # Connect to DataHub
    print("Connecting to DataHub...")
    config = DatahubClientConfig(server="http://localhost:8888")
    graph = DataHubGraph(config)

    # Test dataset URN
    dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.demographics,PROD)"

    # Step 1: Retrieve profile data
    print(f"\nRetrieving profile data for {dataset_urn}...")
    profile = graph.get_latest_timeseries_value(
        entity_urn=dataset_urn,
        aspect_type=DatasetProfileClass,
        filter_criteria_map={}
    )

    if profile:
        print("[OK] Profile found!")
        print(f"  - Row count: {profile.rowCount}")
        print(f"  - Column count: {profile.columnCount}")
        if profile.fieldProfiles:
            print(f"  - Field profiles: {len(profile.fieldProfiles)}")
            for fp in profile.fieldProfiles[:3]:  # Show first 3
                print(f"    * {fp.fieldPath}: unique={fp.uniqueCount}, nulls={fp.nullCount}")
    else:
        print("[FAIL] No profile found! Profiling may not have run.")
        return

    # Step 2: Create and configure the data quality action
    print("\nSetting up Data Quality Action...")

    config = {
        "enabled": True,
        "tests": [
            {
                "name": "demographics_row_count_check",
                "type": "table_row_count",
                "dataset_pattern": "urn:li:dataset:*snowflake*covid19.public.demographics*",
                "params": {
                    "min_rows": "1000",
                    "max_rows": "10000"
                }
            },
            {
                "name": "demographics_column_count_check",
                "type": "table_column_count_between",
                "dataset_pattern": "urn:li:dataset:*snowflake*covid19.public.demographics*",
                "params": {
                    "min_value": "5",
                    "max_value": "20"
                }
            },
            {
                "name": "iso3166_2_not_null_check",
                "type": "column_values_not_null",
                "dataset_pattern": "urn:li:dataset:*snowflake*covid19.public.demographics*",
                "column": "iso3166_2",
                "params": {
                    "max_null_proportion": "0.05"  # Max 5% nulls
                }
            }
        ]
    }

    # Create pipeline context with graph
    ctx = PipelineContext(pipeline_name="test-data-quality", graph=graph)

    # Create the action
    action = DataQualityAction.create(config, ctx)
    print(f"[OK] Action created with {len(config['tests'])} tests")

    # Step 3: Create a dataset change event to trigger the action
    print("\nSimulating dataset change event...")

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

    # Step 4: Process the event (this will run tests and emit assertions)
    print("Running quality tests...")
    try:
        action.act(event_env)
        print("[OK] Tests executed successfully!")
    except Exception as e:
        print(f"[FAIL] Error during test execution: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 5: Verify assertions were created
    print("\nVerifying assertions in DataHub...")

    # Query for assertions
    from datahub.utilities.urns.urn import Urn

    # Search for assertions
    search_query = """
    {
        search(input: {
            type: ASSERTION,
            query: "demographics",
            start: 0,
            count: 10
        }) {
            searchResults {
                entity {
                    ... on Assertion {
                        urn
                        info {
                            type
                            customProperties {
                                key
                                value
                            }
                        }
                    }
                }
            }
        }
    }
    """

    try:
        result = graph.execute_graphql(search_query)
        assertions = result.get("search", {}).get("searchResults", [])

        if assertions:
            print(f"[OK] Found {len(assertions)} assertion(s):")
            for a in assertions:
                entity = a.get("entity", {})
                print(f"  - {entity.get('urn', 'unknown')}")
                info = entity.get("info", {})
                print(f"    Type: {info.get('type', 'unknown')}")
        else:
            print("Note: No assertions found yet (may take a moment to index)")
    except Exception as e:
        print(f"Note: Could not query assertions via GraphQL: {e}")

    print("\n" + "="*60)
    print("Test completed! Check DataHub UI at http://localhost:9002")
    print(f"Navigate to the dataset: {dataset_urn}")
    print("="*60)


if __name__ == "__main__":
    main()
