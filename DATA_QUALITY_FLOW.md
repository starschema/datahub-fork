# DataHub Data Quality - Automatic Testing Flow

## Overview

DataHub automatically runs data quality tests whenever datasets are profiled during ingestion. Tests use **zero-duplication credential sharing** - quality tests reuse the same database credentials configured for ingestion sources.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION (Scheduled, e.g., every 30 minutes)                     │
│    datahub ingest -c snowflake.yml                                   │
│    • Profiles datasets (with stateful optimization)                  │
│    • Emits datasetProfile to Kafka                                   │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2. KAFKA EVENT STREAM                                                │
│    Topic: MetadataChangeLog_Timeseries_v1                            │
│    Event: { entityType: "dataset", aspectName: "datasetProfile" }    │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3. DATA QUALITY ACTION (Auto-triggered)                              │
│    Listens to Kafka → Executes tests → Emits assertions             │
│                                                                       │
│    A. Profile-Based Tests (13 types)                                 │
│       • Uses cached profile data from ingestion                      │
│       • No database connection needed                                │
│       • Examples: table_row_count, column_min_between                │
│                                                                       │
│    B. Query-Based Tests (7 types)                                    │
│       • Executes fresh SQL queries on live data                      │
│       • Uses ingestion source credentials (ZERO DUPLICATION!)        │
│       • Examples: column_values_in_set, table_custom_sql             │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 4. ASSERTION RESULTS                                                 │
│    • Assertions emitted to DataHub                                   │
│    • Visible in UI under dataset → Validations tab                   │
│    • Updated every ingestion run                                     │
└──────────────────────────────────────────────────────────────────────┘
```

## How It Works

### Automatic Profiling

During ingestion, DataHub:
1. Connects to Snowflake (or other source)
2. Profiles datasets (collects row counts, column statistics, etc.)
3. Emits `datasetProfile` aspect to Kafka
4. **Stateful profiling** - only profiles changed tables on subsequent runs

### Automatic Quality Testing

When `datasetProfile` event is received:
1. DataQualityAction auto-triggers (no manual intervention!)
2. Finds all tests matching the dataset pattern
3. Executes profile-based tests using cached profile data
4. Executes query-based tests using database credentials from ingestion source
5. Emits assertion results back to DataHub

### Zero-Duplication Credential Sharing

**Key Innovation:** Query-based tests automatically reuse credentials from ingestion sources.

```
Ingestion Source (configured once in DataHub UI)
  ↓
  Snowflake credentials stored securely in DataHub
  ↓
  DataQualityAction queries DataHub's ingestion source registry
  ↓
  Builds database connection using same credentials
  ↓
  Executes fresh SQL queries for quality tests
```

**No credential duplication required!** Configure your data source once, use it for both ingestion AND quality testing.

## Available Test Types

### Profile-Based Tests (13 types)

Use cached statistics from profiling - **no database connection needed**.

**Table-Level (4 tests):**
- `table_row_count` - Row count within min/max range
- `table_row_count_equals` - Row count equals exact value
- `table_column_count_equals` - Column count equals value
- `table_column_count_between` - Column count within range

**Column-Level (9 tests):**
- `column_values_not_null` - No/few null values
- `column_values_unique` - All values unique
- `column_min_between` - Minimum value within range
- `column_max_between` - Maximum value within range
- `column_mean_between` - Mean value within range
- `column_median_between` - Median value within range
- `column_stddev_between` - Standard deviation within range
- `column_distinct_count_between` - Distinct count within range
- `column_unique_proportion_between` - Proportion of unique values
- `column_null_count_equals` - Null count equals value

### Query-Based Tests (7 types)

Execute fresh SQL queries on live data - **uses ingestion source credentials**.

**Column-Level (6 tests):**
- `column_value_range` - All values within min/max (fresh check)
- `column_values_in_set` - All values in allowed set
- `column_values_not_in_set` - No values in forbidden set
- `column_values_match_regex` - All values match pattern
- `column_values_not_match_regex` - No values match forbidden pattern
- `column_length_between` - String length within range

**Table-Level (1 test):**
- `table_custom_sql` - Custom SQL returns expected result

## Configuration Example

```yaml
# data-quality-action-config.yaml

source:
  type: "kafka"
  config:
    connection:
      bootstrap: "broker:29092"
    topic_routes:
      mcl: "MetadataChangeLog_Timeseries_v1"

# Auto-trigger when datasetProfile aspect is written
filter:
  event_type: "MetadataChangeLogEvent_v1"
  event:
    entityType: "dataset"
    aspectName: "datasetProfile"

action:
  type: "data_quality"
  config:
    enabled: true

    # NO CONNECTORS NEEDED! (Auto-discovered from DataHub)
    # Credentials automatically loaded from ingestion sources

    tests:
      # Profile-based test (uses cached data)
      - name: "table_has_data"
        type: "table_row_count"
        dataset_pattern: "urn:li:dataset:*snowflake*"
        params:
          min_rows: "1"
          max_rows: "100000000"

      # Query-based test (executes fresh SQL)
      - name: "valid_state_codes"
        type: "column_values_in_set"
        dataset_pattern: "urn:li:dataset:*snowflake*demographics*"
        column: "state"
        params:
          value_set: "AL,AK,AZ,AR,CA,CO,CT,..."
```

## Stateful Ingestion for Efficiency

**Why subsequent ingestion runs are faster:**

DataHub uses **stateful ingestion** to track what was already ingested:

1. **First run:** Profiles all datasets (e.g., 100 tables, takes 10 minutes)
2. **Subsequent runs:** Only profiles changed datasets (e.g., 5 tables, takes 30 seconds!)

Stateful ingestion tracks:
- Last profiling timestamp per dataset
- Only re-profiles if `LAST_ALTERED` timestamp changed
- Stores state in DataHub metadata

**This means you can run ingestion frequently (every 15-30 minutes) without performance impact!**

## Real-Time Quality Monitoring

To achieve near-real-time quality monitoring:

1. **Schedule frequent ingestion** (every 15-60 minutes via cron/Airflow)
2. **Stateful ingestion optimizes performance** (only profiles changed tables)
3. **Quality tests auto-trigger** (via Kafka events)
4. **Assertions update in UI** (fresh results every ingestion run)

Example cron for 30-minute updates:
```bash
*/30 * * * * datahub ingest -c snowflake.yml
```

## End-to-End Example

```
Time 10:00 - Ingestion Run #1
  ├─ Snowflake: 100 datasets profiled
  ├─ Kafka: 100 datasetProfile events emitted
  ├─ DataQualityAction: 1700 tests executed (17 tests × 100 datasets)
  └─ Result: All assertions updated in DataHub UI

Time 10:30 - Ingestion Run #2 (stateful)
  ├─ Snowflake: Only 5 datasets changed, only 5 profiled
  ├─ Kafka: 5 datasetProfile events emitted
  ├─ DataQualityAction: 85 tests executed (17 tests × 5 datasets)
  └─ Result: Only changed datasets' assertions updated

Time 11:00 - Ingestion Run #3 (stateful)
  ├─ Snowflake: Only 3 datasets changed, only 3 profiled
  ├─ Kafka: 3 datasetProfile events emitted
  ├─ DataQualityAction: 51 tests executed (17 tests × 3 datasets)
  └─ Result: Only changed datasets' assertions updated
```

**Key Insight:** Stateful ingestion makes frequent ingestion practical!

## Files Reference

- **Configuration:** `data-quality-action-config.yaml`
- **Test Executor:** `datahub-actions/src/datahub_actions/plugin/action/data_quality/test_executor.py`
- **Connector Registry:** `datahub-actions/src/datahub_actions/plugin/action/data_quality/connector_registry.py`
- **Test Templates:** `datahub-actions/src/datahub_actions/plugin/action/data_quality/templates/`
  - `profile_based.py` - 13 profile-based test implementations
  - `query_based.py` - 7 query-based test implementations

## Summary

✅ **Automatic** - Tests run every time datasets are profiled
✅ **Zero Duplication** - Credentials shared from ingestion sources
✅ **Efficient** - Stateful ingestion only processes changed data
✅ **Comprehensive** - 20 test types (13 profile + 7 query)
✅ **Real-time Ready** - Schedule ingestion every 15-60 minutes

Configure your ingestion source once, and quality testing happens automatically!
