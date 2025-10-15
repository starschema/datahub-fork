# DataHub GX Integration - Technical Integration Points

**Status**: Integration investigation completed
**Date**: 2025-10-14

## Summary

Comprehensive investigation of all 4 key integration points needed to build Great Expectations data quality validation as a DataHub Action. All integration points are well-supported by existing infrastructure.

---

## 1. DataHub Actions Framework Integration

### Location
- `datahub-actions/src/datahub_actions/action/action.py`
- `datahub-actions/src/datahub_actions/action/action_registry.py`
- `datahub-actions/setup.py`

### Key Pattern: Action Base Class

```python
from datahub_actions.action.action import Action
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub_actions.event.event_envelope import EventEnvelope

class DataQualityAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> "Action":
        # Initialize action with configuration
        # Access ctx.graph for DataHub API
        return cls(config_dict, ctx)

    def act(self, event: EventEnvelope) -> None:
        # Process events (ENTITY_CHANGE_EVENT_V1)
        # event.event_type, event.payload
        pass

    def close(self) -> None:
        # Cleanup resources
        pass
```

### Registration via Entry Points

In `setup.py`:
```python
entry_points = {
    "datahub_actions.action.plugins": [
        "data_quality = datahub_gx_action.action:DataQualityAction",
    ],
}
```

### PipelineContext Provides
```python
@dataclass
class PipelineContext:
    pipeline_name: str
    graph: Optional[AcrylDataHubGraph]  # For API calls
```

### Event Types
- `EntityChangeEventType.ENTITY_CHANGE_EVENT_V1`: Triggered on entity updates
- Can filter by entity type (datasets) and operation type (CREATE/UPDATE)

---

## 2. Profile Data Retrieval

### Location
- `metadata-ingestion/src/datahub/ingestion/graph/client.py:332-348`

### DataHubGraph Client Pattern

```python
from datahub.ingestion.graph.client import DataHubGraph
from datahub.metadata.schema_classes import DatasetProfileClass

# Available in PipelineContext
graph: DataHubGraph = ctx.graph

# Retrieve dataset profile
profile: Optional[DatasetProfileClass] = graph.get_aspect(
    entity_urn="urn:li:dataset:(urn:li:dataPlatform:mysql,db.schema.table,PROD)",
    aspect_type=DatasetProfileClass,
    version=0  # Latest version
)

if profile:
    # Access profile data
    row_count = profile.rowCount
    column_count = profile.columnCount

    for field_profile in profile.fieldProfiles:
        field_name = field_profile.fieldPath
        null_count = field_profile.nullCount
        unique_count = field_profile.uniqueCount
        min_val = field_profile.min
        max_val = field_profile.max
        mean = field_profile.mean
        median = field_profile.median
        stdev = field_profile.stdev
```

### Aspect Name
- Use `DatasetProfileClass` directly (not string "datasetProfile")
- GraphQL automatically resolves the aspect name

### HTTP Endpoint
- `GET /aspects/{urn}?aspect={aspect}&version={version}`
- Returns 404 if aspect doesn't exist

---

## 3. Existing GX Plugin Integration Patterns

### Location
- `metadata-ingestion-modules/gx-plugin/src/datahub_gx_plugin/action.py`

### Assertion Creation Pattern

```python
import datahub.emitter.mce_builder as builder
from datahub.metadata.com.linkedin.pegasus2avro.assertion import (
    AssertionInfo,
    AssertionType,
    DatasetAssertionInfo,
    DatasetAssertionScope,
    AssertionStdOperator,
    AssertionStdAggregation,
    AssertionStdParameters,
    AssertionStdParameter,
    AssertionStdParameterType,
)

# 1. Create deterministic assertion URN
assertionUrn = builder.make_assertion_urn(
    builder.datahub_guid(
        pre_json_transform({
            "platform": "great-expectations",
            "nativeType": "expect_column_min_to_be_between",
            "nativeParameters": {"min_value": 0, "max_value": 100},
            "dataset": dataset_urn,
            "fields": [field_urn],  # Column field URNs
        })
    )
)

# 2. Create DataHub standard assertion info
assertionInfo = AssertionInfo(
    type=AssertionType.DATASET,
    datasetAssertion=DatasetAssertionInfo(
        dataset=dataset_urn,
        fields=[field_urn],
        scope=DatasetAssertionScope.DATASET_COLUMN,
        operator=AssertionStdOperator.BETWEEN,
        aggregation=AssertionStdAggregation.MIN,
        parameters=AssertionStdParameters(
            minValue=AssertionStdParameter(value="0", type=AssertionStdParameterType.NUMBER),
            maxValue=AssertionStdParameter(value="100", type=AssertionStdParameterType.NUMBER),
        ),
        nativeType="expect_column_min_to_be_between",
        nativeParameters={"min_value": "0", "max_value": "100"},
    ),
    customProperties={"test_suite": "profiling_checks"},
)
```

### Assertion Result Emission

```python
from datahub.metadata.com.linkedin.pegasus2avro.assertion import (
    AssertionRunEvent,
    AssertionResult,
    AssertionResultType,
    AssertionRunStatus,
)
from datahub.emitter.mcp import MetadataChangeProposalWrapper

# Create result event
assertionResult = AssertionRunEvent(
    timestampMillis=int(round(time.time() * 1000)),
    assertionUrn=assertionUrn,
    asserteeUrn=dataset_urn,
    runId=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    result=AssertionResult(
        type=AssertionResultType.SUCCESS,  # or FAILURE
        rowCount=1000,  # Total rows evaluated
        actualAggValue=5.2,  # Observed value (e.g., min=5.2)
        nativeResults={
            "observed_value": "5.2",
            "expected_range": "[0, 100]",
        },
    ),
    status=AssertionRunStatus.COMPLETE,
)

# Emit via MCP
mcp = MetadataChangeProposalWrapper(
    entityUrn=assertionUrn,
    aspect=assertionResult,
)
emitter.emit_mcp(mcp)
```

### Known Expectations Mapping (Lines 391-183)

The existing GX plugin maps GE expectation types to DataHub standard assertions:

```python
{
    "expect_column_min_to_be_between": DataHub MIN + BETWEEN,
    "expect_column_max_to_be_between": DataHub MAX + BETWEEN,
    "expect_column_mean_to_be_between": DataHub MEAN + BETWEEN,
    "expect_column_median_to_be_between": DataHub MEDIAN + BETWEEN,
    "expect_column_stdev_to_be_between": DataHub STDDEV + BETWEEN,
    "expect_column_unique_value_count_to_be_between": DataHub UNIQUE_COUNT + BETWEEN,
    "expect_column_values_to_not_be_null": DataHub NOT_NULL + IDENTITY,
    "expect_column_values_to_be_in_set": DataHub IN + IDENTITY,
    "expect_table_row_count_to_be_between": DataHub ROW_COUNT + BETWEEN,
    "expect_table_column_count_to_equal": DataHub COLUMN_COUNT + EQUAL_TO,
}
```

### Scopes Available
- `DatasetAssertionScope.DATASET_COLUMN`: Column-level assertions
- `DatasetAssertionScope.DATASET_ROWS`: Table-level assertions
- `DatasetAssertionScope.DATASET_SCHEMA`: Schema assertions

---

## 4. Connector Access and Configuration

### Location
- `metadata-ingestion/src/datahub/ingestion/source/sql/sql_common.py`
- `metadata-ingestion/src/datahub/ingestion/source/ge_data_profiler.py`

### SQLAlchemy Engine Access Pattern

**From SQL Source (sql_common.py:413-422)**:
```python
def get_inspectors(self) -> Iterable[Inspector]:
    url = self.config.get_sql_alchemy_url()
    engine = create_engine(url, **self.config.options)
    with engine.connect() as conn:
        inspector = inspect(conn)
        yield inspector
```

**From Profiler (sql_common.py:1264-1273)**:
```python
def get_profiler_instance(self, inspector: Inspector) -> "DatahubGEProfiler":
    from datahub.ingestion.source.ge_data_profiler import DatahubGEProfiler

    return DatahubGEProfiler(
        conn=inspector.bind,  # SQLAlchemy Connection/Engine
        report=self.report,
        config=self.config.profiling,
        platform=self.platform,
        env=self.config.env,
    )
```

### Engine Provides Full Query Capability

**Direct SQL Execution (ge_data_profiler.py:560-562)**:
```python
# Engine can execute any SQL
row_count = self.dataset.engine.execute(get_estimate_script).scalar()

# Complex aggregations already supported
element_values = self.dataset.engine.execute(
    sa.select([
        sa.func.coalesce(
            sa.text(f'APPROXIMATE count(distinct "{column}")')
        ),
    ]).select_from(self._table)
)
```

### Connector Configuration is Sufficient

**No external compute needed** - evidence from profiler (ge_data_profiler.py:268-280):

```python
# GROUP BY queries execute IN the database
results = self.dataset.engine.execute(
    sa.select([
        sa.column(column),
        sa.func.count(sa.column(column)),
    ])
    .select_from(self.dataset._table)
    .where(sa.column(column).is_not(None))
    .group_by(sa.column(column))
).fetchall()
```

### Platform-Specific Optimizations Already Exist

Profiler supports:
- **Snowflake**: Custom median, APPROX functions
- **BigQuery**: APPROX_COUNT_DISTINCT, temp table caching
- **Redshift**: APPROXIMATE count distinct
- **Databricks**: approx_count_distinct, approx_percentile
- **Athena/Trino**: approx_distinct, approx_percentile
- **PostgreSQL/MySQL**: Row count estimates

### Connection Details Available

From connector configuration we can access:
```python
inspector.bind  # SQLAlchemy Engine or Connection
inspector.engine.url  # Database URL
inspector.engine.dialect.name  # Platform name (mysql, postgres, etc.)
```

---

## Implementation Architecture

### Data Flow

```
1. DataHub Event → DataQualityAction.act()
   ↓
2. Extract dataset URN from event
   ↓
3. graph.get_aspect(urn, DatasetProfileClass) → Retrieve profile
   ↓
4. FOR EACH test template:
     ├─ Profile-based tests: Use cached profile data
     │   └─ No database queries
     │
     └─ Query-based tests: Need fresh data
         ├─ Get connector config from DataHub
         ├─ Create SQLAlchemy engine
         └─ Execute validation query IN the database
   ↓
5. Emit assertions:
     ├─ AssertionInfo (defines test)
     └─ AssertionRunEvent (test result)
```

### Two-Tier Validation Architecture

**Tier 1: Profile-Based (70% of tests)**
- Use cached `DatasetProfileClass` data
- No database queries required
- Tests: row_count, null_count, unique_count, min, max, mean, median, stddev

**Tier 2: Query-Based (30% of tests)**
- Execute validation queries using connector
- Query results calculated IN the database
- Only transfer aggregated results (not row-level data)
- Tests: value ranges, regex patterns, cross-table checks

---

## Key Findings

### ✅ Actions Framework
- Simple plugin pattern via entry points
- Access to DataHubGraph client via PipelineContext
- Event-driven architecture for dataset changes

### ✅ Profile Retrieval
- Single method: `graph.get_aspect(urn, DatasetProfileClass)`
- Returns comprehensive profile with row/column statistics
- 404-safe (returns None if not found)

### ✅ Assertion Emission
- Existing patterns in GX plugin fully documented
- Standard assertion types map cleanly to test templates
- Deterministic URN generation prevents duplicates

### ✅ Connector Access
- SQL connectors provide full SQLAlchemy Engine
- All validation queries can execute IN the database
- No external compute infrastructure needed
- Platform-specific optimizations already implemented

---

## Next Steps

With all integration points validated, we're ready to proceed with:

1. **Phase 1: Core Framework**
   - Implement `DataQualityAction` base class
   - Add profile-based test execution
   - Set up assertion emission

2. **Phase 2: Test Templates**
   - Build 24 prebuilt test templates
   - Implement profile-based tests (17 tests)
   - Add query-based tests (7 tests)

3. **Phase 3: Configuration & Scheduling**
   - YAML configuration system
   - Airflow DAG generation
   - Multi-trigger support

All technical dependencies are satisfied by existing DataHub infrastructure.
