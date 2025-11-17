# AI-Generated Assertions - Deployment Guide

## Quick Summary

This implementation allows custom data quality checks created via the AI assistant to automatically execute using the correct database connector when datasets are ingested.

**Key Features**:
- ✅ Zero credential duplication (reuses ingestion source configs)
- ✅ Automatic execution on every ingestion
- ✅ Supports multiple trigger types (ON_INGESTION, ON_PROFILE)
- ✅ Works with Snowflake, PostgreSQL, MySQL (extensible to others)
- ✅ Results stored as AssertionRunEvent timeseries

---

## Files Created

### New Action Plugins
1. `datahub-actions/src/datahub_actions/plugin/action/assertion_executor/`
   - `__init__.py`
   - `action.py` - Main assertion executor logic
   - `config.py` - Configuration model

### Configuration Files
2. `ingestion-source-mapper-action-config.yaml` - Maps datasets to sources
3. `assertion-executor-action-config.yaml` - Executes assertions

### Documentation
4. `AI_ASSERTIONS_IMPLEMENTATION.md` - Comprehensive implementation guide
5. `AI_ASSERTIONS_DEPLOYMENT.md` - This file

### Modified Files
6. `datahub-with-data-quality.yml` - Added volume mounts for new configs

---

## Deployment Steps

### Step 1: Rebuild DataHub Actions Image

If using custom image:

```bash
cd datahub-actions
docker build -t ghcr.io/starschema/datahub-actions-with-governance:latest .
docker push ghcr.io/starschema/datahub-actions-with-governance:latest
```

### Step 2: Restart DataHub Actions

```bash
cd /path/to/datahub
docker compose -f datahub-with-data-quality.yml restart datahub-actions
```

### Step 3: Verify Actions Are Running

```bash
docker logs datahub-datahub-actions-1 -f
```

Look for:
```
Action Pipeline with name 'ingestion_source_mapper' is now running
Action Pipeline with name 'assertion_executor' is now running
Action Pipeline with name 'governance_bot' is now running
Action Pipeline with name 'data_quality' is now running
```

---

## Frontend Integration

### What the AI Assistant Needs to Do

After generating SQL query, call this GraphQL mutation:

```graphql
mutation upsertCustomAssertion($input: UpsertCustomAssertionInput!) {
  upsertCustomAssertion(input: $input) {
    urn
  }
}
```

**Minimal Example**:

```javascript
await upsertAssertion({
  variables: {
    input: {
      entityUrn: datasetUrn,  // Dataset URN from current page
      type: "SQL",
      description: "AI-generated: Row count > 1000",
      platform: { urn: "urn:li:dataPlatform:snowflake" },
      source: { type: "INFERRED" },  // Marks as AI-generated
      sqlAssertion: {
        type: "METRIC",
        statement: "SELECT COUNT(*) FROM table",
        operator: "GREATER_THAN",
        parameters: {
          value: { value: "1000", type: "NUMBER" }
        }
      },
      customProperties: [
        { key: "assertionTriggers", value: "ON_INGESTION,ON_PROFILE" }
      ]
    }
  }
});
```

See `AI_ASSERTIONS_IMPLEMENTATION.md` for complete frontend integration code.

---

## Testing

### 1. Create Test Assertion (via Python)

```python
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    AssertionInfoClass,
    AssertionTypeClass,
    SqlAssertionInfoClass,
    SqlAssertionTypeClass,
    AssertionStdOperatorClass,
    AssertionStdParametersClass,
    AssertionStdParameterClass,
    AssertionSourceClass,
    AssertionSourceTypeClass,
)

emitter = DatahubRestEmitter("http://localhost:8080", token="your_token")

dataset_urn = make_dataset_urn(
    platform="snowflake",
    name="covid19.public.cdc_inpatient_beds_all",
    env="PROD"
)

assertion_urn = f"urn:li:assertion:ai-test-{int(time.time())}"

assertion_info = AssertionInfoClass(
    type=AssertionTypeClass.SQL,
    description="AI-generated test: Row count > 10",
    sqlAssertion=SqlAssertionInfoClass(
        type=SqlAssertionTypeClass.METRIC,
        statement="SELECT COUNT(*) FROM covid19.public.cdc_inpatient_beds_all",
        operator=AssertionStdOperatorClass.GREATER_THAN,
        parameters=AssertionStdParametersClass(
            value=AssertionStdParameterClass(
                value="10",
                type="NUMBER"
            )
        )
    ),
    source=AssertionSourceClass(
        type=AssertionSourceTypeClass.INFERRED  # AI-generated
    ),
    customProperties={
        "assertionTriggers": "ON_INGESTION,ON_PROFILE",
        "aiGenerated": "true"
    }
)

mcp = MetadataChangeProposalWrapper(
    entityUrn=assertion_urn,
    aspect=assertion_info
)
emitter.emit(mcp)

# Link assertion to dataset
from datahub.metadata.schema_classes import AssertionKeyClass
assertion_key = AssertionKeyClass(assertionId="ai-test-{timestamp}")
# ... (link via relationship)
```

### 2. Trigger Execution

**Option A**: Run Snowflake ingestion
```bash
datahub ingest -c snowflake_ingestion.yml
```

**Option B**: Manually emit status aspect
```python
from datahub.metadata.schema_classes import StatusClass

status = StatusClass(removed=False)
mcp = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=status
)
emitter.emit(mcp)
```

### 3. Check Results

**View logs**:
```bash
docker logs datahub-datahub-actions-1 -f | grep -i "assertion"
```

**Query via GraphQL**:
```graphql
{
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.cdc_inpatient_beds_all,PROD)") {
    assertions {
      total
      assertions {
        urn
        runEvents(start: 0, count: 10) {
          runEvents {
            timestampMillis
            status
            result {
              type
              actualAggValue
            }
          }
        }
      }
    }
  }
}
```

---

## Configuration Options

### Ingestion Source Mapper

**File**: `ingestion-source-mapper-action-config.yaml`

```yaml
action:
  type: "ingestion_source_mapper"
  config:
    enabled: true
    property_key: "datahub.ingestion.sourceUrn"  # Where to store mapping
```

### Assertion Executor

**File**: `assertion-executor-action-config.yaml`

```yaml
action:
  type: "assertion_executor"
  config:
    enabled: true
    trigger_on_ingestion: true   # Execute on dataset ingestion
    trigger_on_profile: true     # Execute on dataset profiling
    max_retries: 2               # Retry failed assertions
    timeout_seconds: 60          # SQL execution timeout
    emit_results: true           # Emit AssertionRunEvent
```

---

## Troubleshooting

### Action Not Loading

```bash
docker logs datahub-datahub-actions-1 | grep "ERROR"
```

Common issues:
- Missing volume mount in docker-compose
- Syntax error in config YAML
- Python import error (missing dependencies)

### Assertion Not Executing

1. Check trigger configuration:
   ```bash
   docker logs datahub-datahub-actions-1 | grep "trigger"
   ```

2. Verify dataset→source mapping exists:
   ```graphql
   query {
     dataset(urn: "...") {
       properties {
         customProperties {
           key
           value
         }
       }
     }
   }
   ```
   Should show `datahub.ingestion.sourceUrn`

3. Check assertion trigger type:
   ```graphql
   query {
     assertion(urn: "...") {
       info {
         customProperties {
           key
           value
         }
       }
     }
   }
   ```
   Should show `assertionTriggers`

### SQL Execution Fails

1. Check connector configuration:
   ```bash
   docker logs datahub-datahub-actions-1 | grep "ConnectorRegistry"
   ```

2. Verify ingestion source exists:
   ```graphql
   query {
     listIngestionSources {
       ingestionSources {
         urn
         name
         type
       }
     }
   }
   ```

3. Test SQL manually in database

---

## Monitoring

### Success Metrics

```bash
# Count assertions executed
docker logs datahub-datahub-actions-1 | grep "Executing SQL assertion" | wc -l

# Count successful assertions
docker logs datahub-datahub-actions-1 | grep "PASSED" | wc -l

# Count failed assertions
docker logs datahub-datahub-actions-1 | grep "FAILED" | wc -l
```

### Alert on Failures

```bash
# Get failed assertions
docker logs datahub-datahub-actions-1 | grep "assertion.*FAILED"
```

---

## Next Steps

### 1. Frontend Integration

**File to Modify**: `datahub-web-react/src/app/entityV2/shared/tabs/Dataset/validations/`

See `AI_ASSERTIONS_IMPLEMENTATION.md` for complete TypeScript code.

### 2. Add More Platform Support

**File to Extend**: `datahub-actions/src/datahub_actions/plugin/action/data_quality/connector_registry.py`

Add cases for BigQuery, Redshift, etc.

### 3. UI Enhancements

- List view of AI-generated assertions
- Edit/delete assertions
- Manual re-run button
- Historical trend charts

---

## Architecture Diagram

```
Ingestion
    ↓
┌──────────────────────────────┐
│ IngestionSourceMapper Action │  ← Captures pipeline name
└──────────────────────────────┘
    ↓
Dataset now has source mapping
    ↓
┌──────────────────────────────┐
│   AssertionExecutor Action   │  ← Executes assertions
└──────────────────────────────┘
    ↓
Results stored as AssertionRunEvent
    ↓
UI displays pass/fail status
```

---

## Support

For issues or questions, refer to:
- `AI_ASSERTIONS_IMPLEMENTATION.md` - Complete technical details
- DataHub Actions logs: `docker logs datahub-datahub-actions-1`
- DataHub documentation: https://datahubproject.io/docs/

**Status**: ✅ Backend implementation complete and ready for deployment
