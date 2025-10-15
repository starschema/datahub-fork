# Great Expectations Data Quality Integration Plan

## Project Overview

Build an automated data quality system for DataHub using Great Expectations that:
- Provides 30+ prebuilt test templates (matching OpenMetadata)
- Reuses existing DataHub connector infrastructure to query tables
- Supports multiple trigger mechanisms (scheduled, event-driven, ingestion-coupled)
- No separate container required - extends existing DataHub Actions

## Key Research Findings

### ✅ Connector Infrastructure Already Exists
- **Location**: `metadata-ingestion/src/datahub/ingestion/source/ge_data_profiler.py`
- DataHub already queries tables during profiling using SQLAlchemy connections
- Executes SQL: `COUNT`, `AVG`, `SUM`, `MIN`, `MAX`, `STDDEV`, `MEDIAN`, `DISTINCT COUNT`
- Supports sampling and approximate queries for performance
- Works with: Snowflake, BigQuery, Postgres, MySQL, Redshift, Athena, Databricks, Trino, etc.

### ✅ Great Expectations Integration Exists
- **Location**: `metadata-ingestion-modules/gx-plugin/src/datahub_gx_plugin/action.py`
- DataHub has existing GX integration (DataHubValidationAction)
- Currently manual trigger only (user runs GX checkpoints)
- Emits assertions to DataHub as AssertionRunEvent
- Supports 300+ GX expectations

### ✅ Profile Data Available for Reuse **[CRITICAL FINDING]**
- **Location**: `metadata-ingestion/src/datahub/ingestion/source/ge_data_profiler.py`
- **What's Already Collected** (lines 500-1040):
  - **Table-level**: `row_count`, `column_count`
  - **Column-level**: `null_count`, `null_proportion`, `unique_count`, `unique_proportion`, `cardinality`
  - **Numeric columns**: `min`, `max`, `mean`, `median`, `stddev`, `quantiles`, `histogram`
  - **String columns**: `sample_values`, `distinct_value_frequencies` (for low cardinality)
  - **All columns**: `data_type`, `cardinality` classification
- **Performance Impact**: 70% of validation tests can use this data with **ZERO database queries**
- **Storage**: Profile data already stored as `DatasetProfileClass` aspect in DataHub

### ✅ Connector Infrastructure Fully Capable **[CRITICAL FINDING]**
- **Location**: `metadata-ingestion/src/datahub/ingestion/source/ge_data_profiler.py`
- **Complex Queries Already Supported**:
  - GROUP BY with aggregations (line 575-585: distinct value frequencies)
  - Approximate functions (lines 184-233: `APPROX_COUNT_DISTINCT`, `APPROX_PERCENTILE`)
  - Platform-specific optimizations (Snowflake `MEDIAN`, BigQuery `APPROX_QUANTILES`, etc.)
  - Custom SQL execution via `engine.execute()` (throughout profiler)
- **Query Execution**: All queries run **IN the database** via SQLAlchemy, not in application
- **Data Transfer**: Only results returned (pass/fail + small metrics), no row-level data
- **No External Compute Required**: Databases handle all aggregations, filtering, regex, etc.

### 🔍 Gap Identified: Validation Triggers
**Problem**: Data can change without metadata changing
- Daily ingestion at 00:00 (metadata unchanged)
- Actual data changes throughout the day
- No MetadataChangeLog event → No validation triggered ❌

**Solution**: Multi-trigger architecture (time-based + event-based + ingestion-coupled)

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────┐
│        Validation Trigger Hub                   │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ Scheduler    │  │ Event        │            │
│  │ (Airflow/    │  │ Listener     │            │
│  │  Cron)       │  │ (MCL events) │            │
│  └──────┬───────┘  └──────┬───────┘            │
│         │                  │                     │
│  ┌──────┴──────────────────┴───────┐            │
│  │   Validation Orchestrator       │            │
│  │  - Deduplicates requests        │            │
│  │  - Checks last validation time  │            │
│  │  - Detects data changes         │            │
│  │  - Prioritizes critical tables  │            │
│  └──────────────┬──────────────────┘            │
└─────────────────┼──────────────────────────────┘
                  │
                  ↓
         ┌────────────────────────┐
         │ GX Validation Executor │
         │  - Loads test configs  │
         │  - Gets DB connection  │
         │  - Runs GX validations │
         │  - Emits assertions    │
         └────────────────────────┘
                  │
                  ↓ Uses
         ┌────────────────────────┐
         │ Connector Registry     │
         │  - Reuses ingestion    │
         │    connector configs   │
         │  - SQLAlchemy conns    │
         └────────────────────────┘
```

### Component Architecture

```
datahub-actions/
└── src/datahub_actions/plugin/action/gx_validation/
    ├── __init__.py
    ├── gx_validation_action.py       # Event-driven validation (MCL events)
    ├── gx_validation_scheduler.py    # Time-based validation
    ├── validation_orchestrator.py    # Deduplication & coordination
    ├── connector_registry.py         # Reuse ingestion connectors
    ├── validation_executor.py        # Two-tier execution (profile + query)
    ├── profile_validator.py          # Tier 1: Validate from cached profile data (70%)
    ├── query_validator.py            # Tier 2: Execute DB queries via connector (30%)
    ├── config_loader.py             # Load test configurations
    ├── assertion_emitter.py         # Emit results to DataHub
    ├── templates/
    │   ├── __init__.py
    │   ├── column_tests.py          # 17 column-level test templates
    │   ├── table_tests.py           # 10 table-level test templates
    │   └── cross_table_tests.py     # 1 cross-table test template
    └── utils/
        ├── change_detector.py       # Detect data changes (row count, timestamp)
        └── freshness_checker.py     # Table freshness validation
```

### Data Flow: Profile-First Validation

```
┌─────────────────────────────────────────────────────────────────┐
│                    Validation Request                           │
│              (dataset_urn + test_configs)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              ValidationExecutor.validate_dataset()              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ↓                         ↓
    ┌───────────────────────┐   ┌────────────────────────┐
    │   TIER 1 (70%)        │   │   TIER 2 (30%)        │
    │   ProfileValidator    │   │   QueryValidator       │
    │                       │   │                        │
    │   ✅ Uses cached      │   │   ❌ Needs fresh       │
    │      profile data     │   │      database query    │
    │   ⚡ INSTANT          │   │   🔄 FAST (DB-side)    │
    │   💾 No DB query      │   │   💾 Minimal transfer  │
    └───────────┬───────────┘   └────────┬───────────────┘
                │                         │
                │                         ↓
                │              ┌──────────────────────┐
                │              │  ConnectorRegistry   │
                │              │  Get SQLAlchemy conn │
                │              └──────────┬───────────┘
                │                         │
                │                         ↓
                │              ┌──────────────────────┐
                │              │  Database Executes   │
                │              │  - REGEXP match      │
                │              │  - IN clause         │
                │              │  - LENGTH()          │
                │              │  - Custom SQL        │
                │              │  Returns: pass/fail  │
                │              └──────────┬───────────┘
                │                         │
                └─────────────┬───────────┘
                              │
                              ↓
                ┌──────────────────────────┐
                │   AssertionEmitter       │
                │   Create AssertionResult │
                │   Emit to DataHub        │
                └──────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Framework & Infrastructure
**Goal**: Basic validation execution engine

#### 1.1 Test Template Library
- [ ] Create `templates/column_tests.py` with 17 column-level templates
  - `column_values_not_null` ✅ (uses profile)
  - `column_values_unique` ✅ (uses profile)
  - `column_values_in_set` ❌ (needs query)
  - `column_values_not_in_set` ❌ (needs query) **[NEW - from OpenMetadata]**
  - `column_values_between` ⚠️ (partial - uses min/max from profile)
  - `column_min_between` ✅ (uses profile)
  - `column_max_between` ✅ (uses profile)
  - `column_mean_between` ✅ (uses profile)
  - `column_median_between` ✅ (uses profile)
  - `column_sum_between` ⚠️ (can derive from profile data)
  - `column_stddev_between` ✅ (uses profile)
  - `column_length_between` ❌ (needs query)
  - `column_distinct_count_between` ✅ (uses profile)
  - `column_unique_proportion_between` ✅ (uses profile)
  - `column_values_match_regex` ❌ (needs query)
  - `column_values_not_match_regex` ❌ (needs query)
  - `column_null_count_equals` ✅ (uses profile) **[NEW - from OpenMetadata]**

- [ ] Create `templates/table_tests.py` with 10 table-level templates
  - `table_row_count_between` ✅ (uses profile)
  - `table_row_count_equals` ✅ (uses profile)
  - `table_column_count_equals` ✅ (uses profile)
  - `table_column_count_between` ✅ (uses profile)
  - `table_column_name_exists` ✅ (uses profile) **[NEW - from OpenMetadata]**
  - `table_columns_match_set` ✅ (uses profile)
  - `table_columns_match_ordered_list` ✅ (uses profile)
  - `table_custom_sql` ❌ (needs query)
  - `table_freshness` ❌ (needs query)
  - `table_row_inserted_count_between` ❌ (needs query) **[NEW - from OpenMetadata]**

- [ ] Create `templates/cross_table_tests.py` with 1 cross-table template
  - `compare_tables_for_differences` ❌ (needs query) **[NEW - from OpenMetadata]**

#### 1.2 Profile Validator (Tier 1 - High Priority)
- [ ] Implement `profile_validator.py`
  - Fetch latest DatasetProfileClass for dataset URN
  - Validate tests that can use profile data (17 out of 24 tests)
  - Return assertion results without database queries
  - **Tests supported**:
    - All `*_between` tests using numeric aggregates (min, max, mean, median, stddev)
    - `column_values_not_null` (uses null_count)
    - `column_values_unique` (uses unique_count)
    - `table_row_count_*` (uses row_count)
    - `table_column_*` (uses column_count and schema)
    - `column_null_count_equals` (uses null_count)

#### 1.3 Query Validator (Tier 2)
- [ ] Implement `query_validator.py`
  - Execute tests requiring database queries (7 out of 24 tests)
  - Reuse patterns from `ge_data_profiler.py`
  - Platform-specific SQL generation (REGEXP syntax, etc.)
  - **Tests supported**:
    - `column_values_in_set`, `column_values_not_in_set` (IN clause)
    - `column_values_match_regex`, `column_values_not_match_regex` (REGEXP)
    - `column_length_between` (LENGTH function)
    - `table_custom_sql` (arbitrary SQL)
    - `table_freshness`, `table_row_inserted_count_between` (timestamp queries)
    - `compare_tables_for_differences` (JOIN queries)

#### 1.4 Connector Registry
- [ ] Implement `connector_registry.py`
  - Load connector configs from DataHub Secrets or config files
  - Instantiate appropriate source connectors (MySQLSource, SnowflakeSource, etc.)
  - Provide connection pooling and lifecycle management
  - Extract platform from dataset URN
  - Map platform → connector class

#### 1.5 Validation Executor (Orchestration Layer)
- [ ] Implement `validation_executor.py`
  - Load test configurations (YAML/JSON)
  - Route tests to Tier 1 (ProfileValidator) or Tier 2 (QueryValidator)
  - Collect results from both tiers
  - Handle errors gracefully
  - Emit assertions to DataHub

#### 1.6 Configuration System
- [ ] Design test configuration schema (YAML)
  ```yaml
  dataset: "urn:li:dataset:(...)"
  tests:
    - type: column_values_not_null
      column: customer_id
    - type: table_row_count_between
      min_value: 1000
      max_value: 1000000
  ```
- [ ] Implement `config_loader.py`
  - Load configs from filesystem
  - Validate config schema
  - Support glob patterns for multiple datasets
  - Option to store configs in DataHub (custom aspects)

#### 1.7 Assertion Emitter
- [ ] Implement `assertion_emitter.py`
  - Reuse code from `datahub_gx_plugin/action.py:231-373`
  - Convert validation results → DataHub AssertionRunEvent
  - Emit via DataHub REST/Kafka
  - Track assertion history
  - Support both profile-based and query-based results

**Deliverable**: Can manually trigger validation for a dataset
```python
# Manual test
executor = ValidationExecutor(config)
results = executor.validate_dataset("urn:li:dataset:(...)")
```

---

### Phase 2: Event-Driven Validation
**Goal**: Automatically trigger on metadata changes

#### 2.1 GX Validation Action
- [ ] Implement `gx_validation_action.py` (extends `Action` base class)
  - Listen for MetadataChangeLog events
  - Filter for dataset entity changes
  - Extract dataset URN from event
  - Trigger validation via orchestrator

#### 2.2 Event Filtering
- [ ] Configure event filters
  - Entity type: `dataset`
  - Change type: `UPSERT`
  - Aspect names: `schemaMetadata`, `datasetProperties`, `datasetProfile`

#### 2.3 Action Registration
- [ ] Register action in `datahub_actions/action/action_registry.py`
- [ ] Create action configuration template

**Deliverable**: Validation triggers when dataset metadata changes
```yaml
# gx_validation_action.yaml
name: "metadata_change_validation"
source:
  type: kafka
filter:
  event_type: MetadataChangeLog_v1
  event:
    entityType: dataset
action:
  type: gx_validation
```

---

### Phase 3: Time-Based Validation (Scheduled)
**Goal**: Run validations on schedule, independent of metadata changes

#### 3.1 Validation Orchestrator
- [ ] Implement `validation_orchestrator.py`
  - Track last validation time per dataset
  - Deduplicate validation requests
  - Prioritize critical datasets
  - Implement rate limiting

#### 3.2 Change Detection
- [ ] Implement `utils/change_detector.py`
  - Query table `last_modified` timestamp
  - Query current row count
  - Compare with last known values
  - Detect data changes even if metadata unchanged

#### 3.3 Scheduler Integration Options

**Option A: Airflow DAG** ✅ RECOMMENDED
```python
# airflow/dags/datahub_validation_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datahub_actions.plugin.action.gx_validation import ValidationOrchestrator

def run_validations(**context):
    orchestrator = ValidationOrchestrator(config_path="/configs/validation.yaml")
    orchestrator.run_scheduled_validations()

dag = DAG(
    'datahub_data_quality',
    schedule_interval='0 */2 * * *',  # Every 2 hours
    catchup=False
)

validate_task = PythonOperator(
    task_id='run_data_quality_checks',
    python_callable=run_validations,
    dag=dag
)
```

**Option B: Standalone Scheduler** (fallback if no Airflow)
- [ ] Implement `gx_validation_scheduler.py`
  - Use APScheduler or similar
  - Parse cron expressions
  - Run as daemon process

**Option C: DataHub Actions Built-in Scheduler** (simple)
- [ ] Extend Actions framework with scheduling capability
  - Add `schedule` field to action config
  - Internal scheduler thread

#### 3.4 Freshness Validation
- [ ] Implement `utils/freshness_checker.py`
  - Check table last update time
  - Validate against freshness SLA
  - Emit freshness assertion results

**Deliverable**: Validations run on schedule
```yaml
# Airflow approach
schedule: "0 */2 * * *"  # Every 2 hours

# OR standalone scheduler
scheduler:
  enabled: true
  cron: "0 */2 * * *"
  datasets:
    - urn: "..."
      priority: high
```

---

### Phase 4: Ingestion-Coupled Validation
**Goal**: Run validations during metadata ingestion

#### 4.1 Extend Ingestion Sources
- [ ] Add `data_quality` config to SQL sources
  ```yaml
  source:
    type: mysql
    config:
      profiling:
        enabled: true
      data_quality:  # NEW
        enabled: true
        test_configs_path: "/configs/mysql_tests/"
  ```

#### 4.2 Ingestion Hook
- [ ] Implement validation hook in ingestion pipeline
  - After profiling step
  - Reuse same DB connection
  - Emit assertions alongside metadata

**Deliverable**: Validations run during ingestion
```bash
datahub ingest -c mysql_recipe.yaml
# Runs: metadata extraction → profiling → data quality validation
```

---

### Phase 5: User Experience & Documentation

#### 5.1 Configuration Examples
- [ ] Create example configs for each use case
  - Time-based validation
  - Event-driven validation
  - Ingestion-coupled validation
  - Hybrid approach

#### 5.2 Documentation
- [ ] Write comprehensive docs
  - Architecture overview
  - Quick start guide
  - Configuration reference
  - Template catalog (all 30+ tests)
  - Troubleshooting guide
  - Best practices

#### 5.3 CLI Commands
- [ ] Add CLI commands
  ```bash
  datahub validation run --config validation.yaml
  datahub validation test --dataset "urn:..."
  datahub validation list-templates
  ```

---

### Phase 6: Advanced Features (Optional)

#### 6.1 UI Integration
- [ ] DataHub UI for test configuration
  - Browse available templates
  - Configure tests via UI
  - View test results history
  - Manage schedules

#### 6.2 Alerting
- [ ] Integrate with notification systems
  - Slack notifications on failures
  - Email alerts
  - PagerDuty integration
  - Webhook support

#### 6.3 Test Result Analytics
- [ ] Build analytics dashboard
  - Test pass/fail trends
  - Dataset health scores
  - Coverage metrics
  - Performance statistics

#### 6.4 Optimizations
- [ ] Performance improvements
  - Parallel test execution
  - Intelligent test batching
  - Query result caching
  - Incremental validation (partitions only)
  - Cost estimation and budgeting

## Scheduling Strategy: Airflow vs Standalone

### ✅ Recommended: Use Airflow

**Pros**:
- Already have Airflow container in DataHub stack
- Native scheduling, retry logic, monitoring
- DAG visualization and history
- Easy to manage complex dependencies
- Can trigger validations after data pipelines
- Built-in alerting and notifications

**Implementation**:
```python
# airflow/dags/datahub_data_quality_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'datahub',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'datahub_data_quality',
    default_args=default_args,
    description='DataHub data quality validation',
    schedule_interval='0 */2 * * *',  # Every 2 hours
    catchup=False,
    tags=['datahub', 'data-quality'],
)

def run_critical_validations(**context):
    """Run validations for critical datasets"""
    from datahub_actions.plugin.action.gx_validation import ValidationOrchestrator

    orchestrator = ValidationOrchestrator(
        config_path="/etc/datahub/validation/critical.yaml"
    )
    results = orchestrator.run_scheduled_validations()

    # Push results to XCom for downstream tasks
    return results

def run_standard_validations(**context):
    """Run validations for standard datasets"""
    from datahub_actions.plugin.action.gx_validation import ValidationOrchestrator

    orchestrator = ValidationOrchestrator(
        config_path="/etc/datahub/validation/standard.yaml"
    )
    return orchestrator.run_scheduled_validations()

# Tasks
critical_validation = PythonOperator(
    task_id='validate_critical_datasets',
    python_callable=run_critical_validations,
    dag=dag,
)

standard_validation = PythonOperator(
    task_id='validate_standard_datasets',
    python_callable=run_standard_validations,
    dag=dag,
)

# Run critical first, then standard
critical_validation >> standard_validation
```

### Alternative: Standalone Scheduler (if no Airflow)
Only implement if Airflow not available:
```python
# gx_validation_scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()
scheduler.add_job(
    run_validations,
    CronTrigger.from_crontab('0 */2 * * *'),
    id='data_quality_checks'
)
scheduler.start()
```

## Configuration Examples

### Example 1: Time-Based (Airflow Scheduled)
```yaml
# /etc/datahub/validation/critical.yaml
name: "Critical Dataset Validations"
schedule: "0 */2 * * *"  # Managed by Airflow DAG

datasets:
  - urn: "urn:li:dataset:(urn:li:dataPlatform:mysql,sales.customers,PROD)"
    priority: high
    tests:
      - type: column_values_not_null
        column: customer_id
      - type: table_row_count_between
        min_value: 10000
        max_value: 10000000

  - urn: "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.orders,PROD)"
    priority: high
    tests:
      - type: column_values_unique
        column: order_id
      - type: column_values_between
        column: order_total
        min_value: 0
        max_value: 1000000
```

### Example 2: Event-Driven
```yaml
# /etc/datahub/actions/gx_validation_action.yaml
name: "schema_change_validation"

source:
  type: kafka
  config:
    connection:
      bootstrap: ${KAFKA_BOOTSTRAP_SERVER}
      schema_registry_url: ${SCHEMA_REGISTRY_URL}

filter:
  event_type: MetadataChangeLog_v1
  event:
    entityType: dataset
    aspectName: schemaMetadata

action:
  type: gx_validation
  config:
    test_configs_path: "/etc/datahub/validation/"
    connector_configs_path: "/etc/datahub/connectors/"
```

### Example 3: Ingestion-Coupled
```yaml
# mysql_ingestion.yaml
source:
  type: mysql
  config:
    host_port: mysql:3306
    database: sales
    username: ${MYSQL_USER}
    password: ${MYSQL_PASSWORD}

    profiling:
      enabled: true

    data_quality:
      enabled: true
      test_suite_path: "/configs/mysql_sales_tests.yaml"
      run_after_profiling: true
```

### Example 4: Hybrid (All Triggers)
```yaml
# Comprehensive setup using multiple triggers

# 1. Airflow DAG for time-based (every 2 hours)
# See airflow/dags/datahub_data_quality_dag.py

# 2. DataHub Action for events
# See /etc/datahub/actions/gx_validation_action.yaml

# 3. Ingestion-coupled
# See ingestion recipes with data_quality config

# 4. Manual/On-demand
datahub validation run \
  --dataset "urn:li:dataset:(...)" \
  --config /configs/tests.yaml
```

## Test Template Catalog

**Total: 24 tests** (21 from OpenMetadata + 3 DataHub-specific)

### OpenMetadata Test Coverage Analysis

✅ **Covered (18/21)**: All core OpenMetadata tests implemented
❌ **Missing (3/21)**: Additional tests to implement
➕ **Extras (3)**: DataHub-specific enhancements

#### Missing OpenMetadata Tests:
1. `table_row_inserted_count_between` - Time-based delta validation
2. `compare_tables_for_differences` - Cross-table comparison
3. `column_null_count_equals` - Exact null count assertion (we have null count but not equality check)

### Column-Level Tests (17)

| Template Name | Description | GX Expectation | Parameters | Uses Profile Data? |
|--------------|-------------|----------------|------------|--------------------|
| `column_values_not_null` | No null values | `expect_column_values_to_not_be_null` | - | ✅ Yes (null_count) |
| `column_values_unique` | All values unique | `expect_column_values_to_be_unique` | - | ✅ Yes (unique_count) |
| `column_values_in_set` | Values in allowed set | `expect_column_values_to_be_in_set` | `value_set` | ❌ No (needs query) |
| `column_values_not_in_set` | Values not in forbidden set | `expect_column_values_to_not_be_in_set` | `value_set` | ❌ No (needs query) |
| `column_values_between` | Values in range | `expect_column_values_to_be_between` | `min_value`, `max_value` | ⚠️ Partial (min/max) |
| `column_min_between` | Min value in range | `expect_column_min_to_be_between` | `min_value`, `max_value` | ✅ Yes (min) |
| `column_max_between` | Max value in range | `expect_column_max_to_be_between` | `min_value`, `max_value` | ✅ Yes (max) |
| `column_mean_between` | Mean in range | `expect_column_mean_to_be_between` | `min_value`, `max_value` | ✅ Yes (mean) |
| `column_median_between` | Median in range | `expect_column_median_to_be_between` | `min_value`, `max_value` | ✅ Yes (median) |
| `column_sum_between` | Sum in range | `expect_column_sum_to_be_between` | `min_value`, `max_value` | ⚠️ Partial (can derive) |
| `column_stddev_between` | Std dev in range | `expect_column_stdev_to_be_between` | `min_value`, `max_value` | ✅ Yes (stdev) |
| `column_length_between` | String length range | `expect_column_value_lengths_to_be_between` | `min_value`, `max_value` | ❌ No (needs query) |
| `column_distinct_count_between` | Distinct count range | `expect_column_unique_value_count_to_be_between` | `min_value`, `max_value` | ✅ Yes (unique_count) |
| `column_unique_proportion_between` | Uniqueness ratio | `expect_column_proportion_of_unique_values_to_be_between` | `min_value`, `max_value` | ✅ Yes (unique_proportion) |
| `column_values_match_regex` | Match regex pattern | `expect_column_values_to_match_regex` | `regex` | ❌ No (needs query) |
| `column_values_not_match_regex` | Don't match regex | `expect_column_values_to_not_match_regex` | `regex` | ❌ No (needs query) |
| `column_null_count_equals` | Exact null count | (custom implementation) | `expected_count` | ✅ Yes (null_count) |

### Table-Level Tests (10)

| Template Name | Description | GX Expectation | Parameters | Uses Profile Data? |
|--------------|-------------|----------------|------------|--------------------|
| `table_row_count_between` | Row count in range | `expect_table_row_count_to_be_between` | `min_value`, `max_value` | ✅ Yes (row_count) |
| `table_row_count_equals` | Exact row count | `expect_table_row_count_to_equal` | `value` | ✅ Yes (row_count) |
| `table_column_count_equals` | Exact column count | `expect_table_column_count_to_equal` | `value` | ✅ Yes (column_count) |
| `table_column_count_between` | Column count range | `expect_table_column_count_to_be_between` | `min_value`, `max_value` | ✅ Yes (column_count) |
| `table_column_name_exists` | Column exists | `expect_column_to_exist` | `column_name` | ✅ Yes (schema) |
| `table_columns_match_set` | Columns match set | `expect_table_columns_to_match_set` | `column_set` | ✅ Yes (schema) |
| `table_columns_match_ordered_list` | Columns in order | `expect_table_columns_to_match_ordered_list` | `column_list` | ✅ Yes (schema) |
| `table_custom_sql` | Custom SQL query | (custom implementation) | `sql`, `expected_result` | ❌ No (needs query) |
| `table_freshness` | Data freshness check | (custom implementation) | `timestamp_column`, `max_age_hours` | ❌ No (needs query) |
| `table_row_inserted_count_between` | Recent inserts count | (custom implementation) | `timestamp_column`, `time_window_hours`, `min_count`, `max_count` | ❌ No (needs query) |

### Cross-Table Tests (1)

| Template Name | Description | Implementation | Parameters | Uses Profile Data? |
|--------------|-------------|----------------|------------|--------------------|
| `compare_tables_for_differences` | Compare two tables | (custom SQL JOIN) | `target_table_urn`, `key_columns`, `compare_columns`, `tolerance` | ❌ No (needs query) |

### Profile Data Reuse Summary

**✅ Can Use Profile Data (70%)**: 17 out of 24 tests
- No database query needed - instant validation
- Works from cached DatasetProfileClass

**❌ Requires Database Query (30%)**: 7 out of 24 tests
- Regex matching (2 tests)
- Set membership (2 tests)
- String length (1 test)
- Custom SQL (1 test)
- Time-based tests (3 tests)
- Cross-table comparison (1 test)

**All queries execute IN the database via existing connector infrastructure - no external compute required.**

## Technical Decisions

### 1. Scheduling: Airflow ✅
- **Decision**: Use Airflow for time-based scheduling
- **Rationale**: Already in stack, better monitoring, DAG visualization
- **Alternative**: Standalone scheduler (fallback option)

### 2. Test Configuration: YAML Files
- **Decision**: YAML-based configuration files
- **Rationale**: Easy to version control, human-readable, standard format
- **Future**: Consider DataHub custom aspects for UI-managed configs

### 3. Connector Reuse: Direct Integration ✅
- **Decision**: Reuse ingestion connector instances and connections
- **Rationale**: Avoid duplicate configs, leverage existing optimizations
- **Implementation**: ConnectorRegistry with lazy loading
- **Evidence**: Profiler already uses SQLAlchemy connections for complex queries (see `ge_data_profiler.py:575-585`)

### 4. Profile Data Reuse Architecture ✅ **NEW**
- **Decision**: Two-tier validation system - profile-based (fast) + query-based (complete)
- **Rationale**: 70% of tests can use existing profile data with zero database queries
- **Performance Impact**:
  - Profile-based tests: **Instant** (no DB query)
  - Query-based tests: **Fast** (database executes aggregations, not application)
- **Implementation**:
  ```python
  class ValidationExecutor:
      def validate_dataset(self, dataset_urn, tests):
          profile = self.get_latest_profile(dataset_urn)  # From DataHub
          results = []

          # TIER 1: Profile-based (70% of tests)
          for test in tests:
              if test.type in PROFILE_BASED_TESTS:
                  results.append(self.validate_from_profile(test, profile))
              else:
                  tests_needing_db.append(test)

          # TIER 2: Query-based (30% of tests)
          if tests_needing_db:
              conn = self.connector_registry.get_connection(dataset_urn)
              ge_dataset = self._create_ge_dataset(conn, dataset_urn)
              for test in tests_needing_db:
                  results.append(self._execute_db_test(ge_dataset, test))

          return results
  ```

### 5. Query Execution Location ✅ **CRITICAL**
- **Decision**: ALL validation queries execute IN the database (not application)
- **Rationale**: No external compute needed - databases handle aggregations efficiently
- **Evidence**:
  - Profiler already executes GROUP BY, APPROX_COUNT_DISTINCT, PERCENTILE queries
  - GX plugin supports RuntimeQueryBatchSpec for arbitrary SQL
  - All platforms support REGEXP, LENGTH, IN clause operators
- **Architecture**:
  - SQLAlchemy engine → Database executes query → Returns only results
  - No row-level data transfer to application
  - Minimal network overhead (pass/fail + small metrics)

### 6. Trigger Strategy: Multi-Trigger
- **Decision**: Support all trigger types (time, event, ingestion)
- **Rationale**: Different use cases need different triggers
- **Orchestrator**: Centralized deduplication and coordination

### 7. No Separate Container
- **Decision**: Extend existing datahub-actions container
- **Rationale**: Reduce operational complexity, reuse infrastructure
- **Deployment**: Install GX dependencies in actions container

## Success Metrics

- [ ] 24 test templates available (21 from OpenMetadata + 3 DataHub-specific)
- [ ] 70% of tests use cached profile data (zero database queries)
- [ ] 30% of tests execute queries IN the database (no external compute)
- [ ] Validations run on schedule (Airflow DAG)
- [ ] Validations trigger on metadata changes
- [ ] Reuses connector infrastructure (no duplicate configs)
- [ ] Assertions visible in DataHub UI
- [ ] Documentation complete
- [ ] Example configurations for each trigger type

### Test Coverage vs OpenMetadata
- ✅ **18/21** core OpenMetadata tests covered
- ❌ **3/21** OpenMetadata tests to implement:
  - `table_row_inserted_count_between`
  - `compare_tables_for_differences`
  - `column_null_count_equals`
- ➕ **3 extras**: DataHub-specific enhancements (`column_distinct_count_between`, `column_unique_proportion_between`, improved profiling integration)

## Dependencies

### Python Packages
- `acryl-great-expectations` (already used by DataHub)
- `acryl-datahub-actions`
- `sqlalchemy` (already used)
- `pydantic` (already used)
- `pyyaml`

### Infrastructure
- DataHub Actions container (existing)
- Airflow container (existing)
- Kafka (existing)
- DataHub GMS (existing)

### Optional
- `apscheduler` (only if not using Airflow)

## Migration Path

### For Existing DataHub Users
1. Deploy updated datahub-actions container with GX validation plugin
2. Create Airflow DAG for scheduled validations
3. Create test configuration files
4. Start with event-driven validation (no schedule needed)
5. Gradually add time-based validations
6. Eventually add ingestion-coupled validations

### Rollout Strategy
1. **Pilot**: Single critical dataset with both triggers
2. **Expand**: Add 10-20 high-priority datasets
3. **Scale**: Enable for all datasets with pattern-based configs
4. **Optimize**: Tune schedules, add custom tests

## Questions & Decisions Needed

- [ ] Airflow DAG naming convention?
- [ ] Where to store test configs in repo? (`docker/validation/` or `.datahub/validation/`?)
- [ ] Default validation schedule? (Recommend: every 2 hours)
- [ ] Assertion retention policy? (How long to keep results?)
- [ ] Alert thresholds? (Fail once vs fail N times)
- [ ] Should we support Great Expectations Cloud integration?

## References

### Code Locations
- Existing GX integration: `metadata-ingestion-modules/gx-plugin/src/datahub_gx_plugin/action.py`
- Profiler: `metadata-ingestion/src/datahub/ingestion/source/ge_data_profiler.py`
- Actions framework: `datahub-actions/src/datahub_actions/`
- SQL connectors: `metadata-ingestion/src/datahub/ingestion/source/sql/`

### Documentation
- DataHub GX docs: https://docs.datahub.com/docs/metadata-ingestion/integration_docs/great-expectations
- OpenMetadata data quality: https://docs.open-metadata.org/latest/how-to-guides/data-quality-observability/quality
- Great Expectations: https://docs.greatexpectations.io/

---

**Last Updated**: 2025-10-14
**Status**: Planning Phase - Research Complete ✅
**Owner**: [Your Name]

## Research Summary

### Key Findings:
1. ✅ **OpenMetadata Coverage**: 18/21 tests covered, 3 additional tests identified
2. ✅ **Profile Data Reuse**: 70% of tests can use cached profile data (zero queries)
3. ✅ **Connector Sufficiency**: 100% of tests can execute via existing connectors
4. ✅ **No External Compute**: All queries execute IN the database
5. ✅ **Performance**: Tier 1 (instant) + Tier 2 (fast, DB-side aggregations)

### Next Steps:
- Proceed to Phase 1: Core Framework Implementation
- Start with `profile_validator.py` (high-value, low-effort)
- Then implement `query_validator.py` (reuse profiler patterns)
- Build on existing GX plugin for assertion emission
