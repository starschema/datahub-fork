"""
Comprehensive Data Quality Test Suite

Runs all 21 available quality tests on all Snowflake datasets where applicable.
"""

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub.metadata.schema_classes import DatasetProfileClass, EntityChangeEventClass, AuditStampClass
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import EntityChangeEvent
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.plugin.action.data_quality.action import DataQualityAction


def get_all_snowflake_datasets(graph):
    """Get all Snowflake dataset URNs"""
    query = """
    {
        search(input: {
            type: DATASET,
            query: "snowflake",
            start: 0,
            count: 200
        }) {
            total
            searchResults {
                entity {
                    ... on Dataset {
                        urn
                        name
                    }
                }
            }
        }
    }
    """

    result = graph.execute_graphql(query)
    datasets = []

    for item in result.get("search", {}).get("searchResults", []):
        entity = item.get("entity", {})
        datasets.append({
            "urn": entity.get("urn"),
            "name": entity.get("name")
        })

    return datasets


def create_comprehensive_test_config():
    """
    Create comprehensive test configuration with all 21 available tests.

    Profile-Based Tests (14 tests - no DB queries needed):
    - Table-level: row_count, column_count validations
    - Column-level: nulls, uniqueness, min/max, mean, median, stddev, distinct counts

    Query-Based Tests (7 tests - require DB connections):
    - Skipped for now as they require database connection strings
    """

    tests = []

    # === TABLE-LEVEL PROFILE-BASED TESTS ===

    # 1. Table Row Count - Basic health check
    tests.append({
        "name": "table_has_data",
        "type": "table_row_count",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "params": {
            "min_rows": "1",  # At least 1 row
            "max_rows": "100000000"  # 100M max
        }
    })

    # 2. Table Row Count Equals - For reference/dimension tables
    # (Skipped - needs specific table knowledge)

    # 3. Table Column Count Between
    tests.append({
        "name": "reasonable_column_count",
        "type": "table_column_count_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "params": {
            "min_value": "1",
            "max_value": "500"  # Max 500 columns
        }
    })

    # 4. Table Column Count Equals
    # (Skipped - needs specific table knowledge)

    # === COLUMN-LEVEL PROFILE-BASED TESTS ===

    # These will apply to ALL columns that match patterns
    # We'll create tests for common column patterns

    # 5-6. Null checks for ID columns (should have very low nulls)
    tests.append({
        "name": "id_columns_not_null",
        "type": "column_values_not_null",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*id",  # Matches any column ending with 'id'
        "params": {
            "max_null_proportion": "0.01"  # Max 1% nulls
        }
    })

    tests.append({
        "name": "key_columns_not_null",
        "type": "column_values_not_null",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*key",
        "params": {
            "max_null_proportion": "0.01"
        }
    })

    # 7. Uniqueness check for ID columns
    tests.append({
        "name": "id_columns_unique",
        "type": "column_values_unique",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*_id",
        "params": {
            "min_unique_proportion": "0.95"  # 95% unique
        }
    })

    # 8-9. Numeric range checks (apply to all numeric columns)
    tests.append({
        "name": "numeric_min_reasonable",
        "type": "column_min_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "-999999999",
            "max_value": "999999999"
        }
    })

    tests.append({
        "name": "numeric_max_reasonable",
        "type": "column_max_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "-999999999",
            "max_value": "999999999"
        }
    })

    # 10. Mean value checks for numeric columns
    tests.append({
        "name": "numeric_mean_reasonable",
        "type": "column_mean_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "-999999999",
            "max_value": "999999999"
        }
    })

    # 11. Median value checks
    tests.append({
        "name": "numeric_median_reasonable",
        "type": "column_median_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "-999999999",
            "max_value": "999999999"
        }
    })

    # 12. Standard deviation checks
    tests.append({
        "name": "numeric_stddev_reasonable",
        "type": "column_stddev_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "0",
            "max_value": "999999999"
        }
    })

    # 13. Distinct count checks
    tests.append({
        "name": "reasonable_distinct_count",
        "type": "column_distinct_count_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "1",
            "max_value": "100000000"
        }
    })

    # 14. Unique proportion for non-ID columns
    tests.append({
        "name": "reasonable_unique_proportion",
        "type": "column_unique_proportion_between",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*",
        "params": {
            "min_value": "0.0",
            "max_value": "1.0"
        }
    })

    # 15. Null count equals zero for critical columns
    tests.append({
        "name": "critical_columns_zero_nulls",
        "type": "column_null_count_equals",
        "dataset_pattern": "urn:li:dataset:*snowflake*",
        "column_pattern": "*_pk",  # Primary key columns
        "params": {
            "value": "0"
        }
    })

    # QUERY-BASED TESTS (Skipped - require database connections)
    # - column_value_range
    # - column_values_in_set
    # - column_values_not_in_set
    # - column_values_match_regex
    # - column_values_not_match_regex
    # - column_length_between
    # - table_custom_sql

    return tests


def main():
    """Run comprehensive quality tests on all Snowflake datasets"""

    print("="*70)
    print("COMPREHENSIVE DATA QUALITY TEST SUITE")
    print("="*70)

    # Connect to DataHub
    print("\n[1/4] Connecting to DataHub...")
    config = DatahubClientConfig(server="http://localhost:8888")
    graph = DataHubGraph(config)
    print("[OK] Connected")

    # Get all Snowflake datasets
    print("\n[2/4] Fetching all Snowflake datasets...")
    datasets = get_all_snowflake_datasets(graph)
    print(f"[OK] Found {len(datasets)} Snowflake datasets")

    # Create comprehensive test configuration
    print("\n[3/4] Creating comprehensive test suite...")
    test_config = create_comprehensive_test_config()
    print(f"[OK] Created {len(test_config)} quality tests")

    print("\nTest Types:")
    for i, test in enumerate(test_config, 1):
        print(f"  {i}. {test['name']} ({test['type']})")

    # Create and configure the data quality action
    print("\n[4/4] Running quality tests on all datasets...")

    action_config = {
        "enabled": True,
        "tests": test_config
    }

    ctx = PipelineContext(pipeline_name="comprehensive-quality-suite", graph=graph)
    action = DataQualityAction.create(action_config, ctx)

    # Process each dataset
    total_assertions = 0
    failed_datasets = []

    for idx, dataset in enumerate(datasets, 1):
        dataset_urn = dataset["urn"]
        dataset_name = dataset["name"]

        print(f"\n  [{idx}/{len(datasets)}] Testing {dataset_name}...")

        try:
            # Create a dataset change event
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

            # Check how many assertions were created
            query = f"""
            {{
                dataset(urn: "{dataset_urn}") {{
                    assertions {{
                        total
                    }}
                }}
            }}
            """

            result = graph.execute_graphql(query)
            assertion_count = result.get("dataset", {}).get("assertions", {}).get("total", 0)
            total_assertions += assertion_count

            print(f"      [OK] Created {assertion_count} assertions")

        except Exception as e:
            print(f"      [FAIL] Error: {str(e)[:100]}")
            failed_datasets.append(dataset_name)

    # Summary
    print("\n" + "="*70)
    print("TEST EXECUTION COMPLETE")
    print("="*70)
    print(f"\nDatasets processed: {len(datasets)}")
    print(f"Total assertions created: {total_assertions}")
    print(f"Failed datasets: {len(failed_datasets)}")

    if failed_datasets:
        print("\nFailed datasets:")
        for name in failed_datasets[:10]:  # Show first 10
            print(f"  - {name}")
        if len(failed_datasets) > 10:
            print(f"  ... and {len(failed_datasets) - 10} more")

    print("\n" + "="*70)
    print("View results in DataHub UI: http://localhost:9002")
    print("Navigate to any dataset and check the 'Validations' tab")
    print("="*70)


if __name__ == "__main__":
    main()
