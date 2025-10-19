# Great Expectations Data Quality Integration - Deployment Guide

## Summary

You have successfully implemented a Great Expectations-inspired data quality integration for DataHub with **21 pre-built test templates** that work with profile data (no database queries required for most tests).

## Current Status

✅ **Implementation Complete**: All code is working and tested locally
✅ **Profile Data Available**: 187 Snowflake datasets profiled
✅ **Tests Validated**: Successfully created 3 assertions on COVID19.PUBLIC.DEMOGRAPHICS dataset
✅ **Configuration Ready**: YAML config file created for 14+ quality tests

## Deployment Options

### Option 1: Run After Each Ingestion (RECOMMENDED for now)

This is the simplest approach while your code is still in development.

**Step 1**: Run your Snowflake ingestion with profiling enabled

**Step 2**: Run the quality test script:
```bash
cd H:/HCLTech/Development/datahub
python test_gx_integration.py
```

**What it does**:
- Reads profile data for each dataset
- Runs all configured quality tests
- Emits assertions to DataHub
- Assertions appear in UI under "Validations" tab

**To automate**: Add this to your ingestion script/pipeline as a post-ingestion step.

---

### Option 2: Docker Actions (Event-Driven - PRODUCTION READY) ✅

**Complete automated setup with UI-based ingestion support and data quality testing.**

This deployment includes:
- ✅ **Executor Action**: Enables UI-based Snowflake ingestion
- ✅ **Data Quality Action**: Automatic quality testing on ingestion
- ✅ **Single Command Deployment**: Unified compose file

**Requirements**:
1. Build custom `datahub-actions` Docker image
2. Configuration files (already created)
3. Single Docker Compose file

**Steps**:

1. **Build Custom Image**:
```bash
cd datahub-actions
docker build -t my-datahub-actions:latest .
```

**Expected build output**:
- ✅ `uv` package installer installed
- ✅ `acryl-executor-0.2.6` installed
- ✅ `sqlalchemy-2.0.44` installed
- ✅ Entry points verified for `executor` and `data_quality`

2. **Deploy Full Stack** (Single Command):
```bash
# From repository root
docker-compose -f datahub-with-data-quality.yml up -d
```

**Alternative (Override approach)**:
```bash
# If you prefer the quickstart base + override
cd docker/quickstart
docker-compose -f docker-compose.quickstart.yml -f docker-compose-data-quality.override.yml up -d
```

3. **Verify Both Actions Running**:
```bash
docker logs quickstart-datahub-actions-1 2>&1 | grep "is now running"
```

**Expected output**:
```
Action Pipeline with name 'ingestion_executor' is now running.
Action Pipeline with name 'data_quality_monitoring' is now running.
```

**What it does**:
- 🎯 **Listens to Kafka events** (MetadataChangeLog) for dataset changes
- 🚀 **Processes UI-based ingestion requests** from DataHub UI
- ✅ **Automatically runs 14 quality tests** when datasets are ingested
- 📊 **Emits assertions** to DataHub for each test result
- 🔄 **No manual intervention needed**

---

## Test Types Available (21 total)

### Profile-Based (14 tests - No DB queries):

**Table-Level**:
1. `table_row_count` - Validate row count is within range
2. `table_row_count_equals` - Exact row count match
3. `table_column_count_between` - Column count within range
4. `table_column_count_equals` - Exact column count

**Column-Level**:
5. `column_values_not_null` - Max null proportion check
6. `column_values_unique` - Min uniqueness proportion
7. `column_min_between` - Min value range
8. `column_max_between` - Max value range
9. `column_mean_between` - Mean value range
10. `column_median_between` - Median value range
11. `column_stddev_between` - Standard deviation range
12. `column_distinct_count_between` - Distinct values count
13. `column_unique_proportion_between` - Uniqueness ratio
14. `column_null_count_equals` - Exact null count

### Query-Based (7 tests - Require DB connection):
15. `column_value_range` - Query actual min/max from DB
16. `column_values_in_set` - Values must be in allowed list
17. `column_values_not_in_set` - Values must NOT be in list
18. `column_values_match_regex` - Pattern matching
19. `column_values_not_match_regex` - Negative pattern matching
20. `column_length_between` - String length validation
21. `table_custom_sql` - Custom SQL assertion

---

## Example Configuration

```yaml
# data-quality-action-config.yaml
action:
  type: "data_quality"
  config:
    enabled: true
    tests:
      # Basic health check - all tables should have data
      - name: "table_has_data"
        type: "table_row_count"
        dataset_pattern: "urn:li:dataset:*snowflake*"
        params:
          min_rows: "1"
          max_rows: "100000000"

      # Null checks for critical columns
      - name: "fips_not_null"
        type: "column_values_not_null"
        dataset_pattern: "urn:li:dataset:*snowflake*demographics*"
        column: "fips"
        params:
          max_null_proportion: "0.01"  # Max 1% nulls

      # Uniqueness check
      - name: "fips_unique"
        type: "column_values_unique"
        dataset_pattern: "urn:li:dataset:*snowflake*demographics*"
        column: "fips"
        params:
          min_unique_proportion: "0.95"  # 95% unique

      # Statistical validation
      - name: "population_reasonable"
        type: "column_mean_between"
        dataset_pattern: "urn:li:dataset:*snowflake*demographics*"
        column: "total_population"
        params:
          min_value: "0"
          max_value: "10000000"
```

---

## Viewing Results

**In DataHub UI (http://localhost:9002)**:

1. Search for your dataset (e.g., "demographics")
2. Click on the dataset
3. Navigate to the **"Validations"** or **"Quality"** tab
4. See all assertions with pass/fail status

**Via API**:
```bash
curl -X POST "http://localhost:8888/api/graphql" -H "Content-Type: application/json" -d '{
  "query": "{
    dataset(urn: \"urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.demographics,PROD)\") {
      assertions {
        total
        assertions {
          urn
        }
      }
    }
  }"
}'
```

---

## Next Steps

**Immediate (Today)**:
1. Use Option 1 (script approach) after each ingestion
2. Verify assertions appear in DataHub UI
3. Adjust test thresholds based on actual data

**Short Term (This Week)**:
1. Expand tests to cover more datasets
2. Add column-specific tests for known data quality issues
3. Build custom Docker image (Optional)

**Long Term (Production)**:
1. Deploy Option 2 (Docker Actions) for event-driven testing
2. Set up alerting for failed assertions
3. Integrate with CI/CD pipeline

---

## Neo4j Graph Database

DataHub includes an **optional Neo4j container** for graph-based lineage and relationship queries.

### Configuration Options

**Option A: Use External Neo4j** (Current Setup)
- Your local Neo4j instance at `localhost:7474` and `localhost:7687`
- DataHub configured with `SKIP_NEO4J_CHECK=true`
- GMS points to `host.docker.internal:7687` (Bolt) and `:7474` (HTTP)

**Option B: Use DataHub's Containerized Neo4j**
- Uncomment the `neo4j` service in `datahub-with-data-quality.yml`
- Standard Neo4j 4.4.9 Community Edition
- **APOC plugin pre-installed** for advanced graph operations
- Fully accessible from external applications

### External Access to Neo4j

**Whether using containerized or local Neo4j, you can:**

✅ **Neo4j Browser UI**: `http://localhost:7474`
- Credentials: `neo4j / datahub` (containerized) or `neo4j / P@ssword1` (external)
- Run Cypher queries, visualize graphs

✅ **Bolt Protocol**: `bolt://localhost:7687`
- Connect from Python, Java, JavaScript, etc.
- Use any Neo4j driver

✅ **Write Custom Data**:
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "datahub")  # or P@ssword1
)

with driver.session(database="graph.db") as session:
    # Your custom nodes/relationships
    session.run("CREATE (n:MyApp:CustomEntity {name: 'example'})")

    # Query DataHub's lineage data
    session.run("MATCH (d:dataset)-[:DownstreamOf]->(d2) RETURN d, d2")
```

### Important Notes

⚠️ **Schema Compatibility**:
- DataHub uses specific node labels (`:dataset`, `:dataJob`, etc.)
- URN format: `urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD)`
- Check `entity-registry.yml` for DataHub's schema

⚠️ **Sync Considerations**:
- Writing directly to Neo4j won't update Elasticsearch
- For modifying DataHub metadata, use DataHub's APIs instead
- Custom data should use separate node labels (e.g., `:MyApp:Entity`)

✅ **Recommended Approach**:
- Read DataHub's graph data freely
- Write custom data alongside DataHub data (separate labels)
- Link your data TO DataHub nodes via relationships

---

## Troubleshooting

### Data Quality Actions

**"No assertions showing in UI"**:
- Check assertions exist: Run GraphQL query (see "Viewing Results" section)
- Hard refresh browser (Ctrl+F5)
- Check correct tab (may be "Quality", "Validations", or "Assertions")

**"Tests not running"**:
- Verify profile data exists (check Elasticsearch)
- Check action logs: `docker logs quickstart-datahub-actions-1`
- Verify configuration file syntax (YAML)
- Confirm both actions are running: `docker logs quickstart-datahub-actions-1 | grep "is now running"`

**"Profile data missing"**:
- Re-run ingestion with `profiling.enabled: true`
- Check ingestion logs for errors
- Verify Elasticsearch has profile data

### UI-Based Ingestion

**"Ingestion stuck in pending"**:
- ✅ **Fixed**: Executor action now included in custom datahub-actions image
- Verify executor is running: `docker logs quickstart-datahub-actions-1 | grep executor`
- Check for errors: `docker logs quickstart-datahub-actions-1 | grep ERROR`

**"Connection test failing"**:
- Verify Snowflake credentials in DataHub UI
- Check network connectivity from container
- Review executor logs for detailed error messages

**"uv not found in PATH"**:
- ✅ **Fixed**: `uv` package installer now included in Dockerfile
- Rebuild image: `cd datahub-actions && docker build -t my-datahub-actions:latest .`

### Container Issues

**"Container won't start"**:
- Check logs: `docker logs quickstart-datahub-actions-1`
- Verify image built successfully: `docker images | grep my-datahub-actions`
- Ensure config files exist and are mounted correctly

**"Entry point not found"**:
- ✅ **Fixed**: Resolved by using system Python instead of virtualenv
- Verify build completed: Check for "Entry point verification passed" in build logs

---

## Files Created

### Configuration Files
- `datahub-with-data-quality.yml` - **Unified Docker Compose file** (RECOMMENDED)
- `data-quality-action-config.yaml` - Data quality action configuration (14 tests)
- `executor-action-config.yaml` - Executor action configuration (UI ingestion)
- `docker/quickstart/docker-compose-data-quality.override.yml` - Docker override (alternative)

### Test Scripts
- `test_gx_integration.py` - Test script for single dataset
- `run_all_quality_tests.py` - Batch script for all datasets

### Docker Build
- `datahub-actions/Dockerfile` - Custom image with executor + data_quality actions
- `datahub-actions/start_actions.sh` - Multi-pipeline startup script
- `datahub-actions/setup.py` - Updated with data_quality extra dependencies

## Code Location

- Action implementation: `datahub-actions/src/datahub_actions/plugin/action/data_quality/`
- Test templates: `datahub-actions/src/datahub_actions/plugin/action/data_quality/templates/`
- Tests: `datahub-actions/tests/unit/plugin/action/data_quality/`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     DataHub UI (Port 9002)                      │
│          - Submit Snowflake ingestion requests                  │
│          - View data quality assertions/results                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DataHub GMS (Port 8888)                      │
│          - GraphQL/REST APIs                                    │
│          - Writes to Kafka + Elasticsearch + Neo4j              │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Kafka (MetadataChangeLog_v1)                    │
│          - Event stream for all metadata changes                │
└──────┬──────────────────────────────────────────────────────────┘
       │
       │  ┌──────────────────────────────────────────────┐
       ├──┤ datahub-actions (Custom Image)               │
       │  │                                              │
       │  │  ┌────────────────────────────────────────┐ │
       │  │  │ Executor Action                        │ │
       │  │  │ - Processes UI ingestion requests      │ │
       │  │  │ - Creates venvs with uv                │ │
       │  │  │ - Runs Snowflake ingestion             │ │
       │  │  └────────────────────────────────────────┘ │
       │  │                                              │
       │  │  ┌────────────────────────────────────────┐ │
       │  │  │ Data Quality Action                    │ │
       │  │  │ - Listens for dataset changes          │ │
       │  │  │ - Runs 14 quality tests                │ │
       │  │  │ - Emits assertions to DataHub          │ │
       │  │  └────────────────────────────────────────┘ │
       │  └──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Storage Layer                                                  │
│  - Elasticsearch: Search/query metadata                         │
│  - MySQL: Primary metadata storage                              │
│  - Neo4j: Graph relationships (optional)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Reference

### Start Everything
```bash
# Build image first
cd datahub-actions && docker build -t my-datahub-actions:latest .

# Start stack
cd .. && docker-compose -f datahub-with-data-quality.yml up -d
```

### Check Status
```bash
# Verify actions running
docker logs quickstart-datahub-actions-1 | grep "is now running"

# Check for errors
docker logs quickstart-datahub-actions-1 | grep ERROR

# View recent logs
docker logs --tail 100 -f quickstart-datahub-actions-1
```

### Access Points
- **DataHub UI**: http://localhost:9002
- **GMS API**: http://localhost:8888
- **Neo4j Browser**: http://localhost:7474 (if using containerized)
- **Elasticsearch**: http://localhost:9200
