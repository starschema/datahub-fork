# AI-Generated Assertions with Auto-Execution - Implementation Guide

## Overview

This implementation enables custom data quality checks created via the AI assistant to automatically execute using the correct connector when datasets are ingested or profiled.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER WORKFLOW                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                 1. User creates custom quality check via AI Assistant
                                    │
                 2. AI validates rule and generates SQL query
                                    │
                 3. Frontend calls upsertCustomAssertion GraphQL mutation
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATAHUB STORAGE                                 │
│                                                                          │
│  • Assertion stored with:                                               │
│    - type: SQL                                                           │
│    - sqlAssertion: { statement, operator, parameters }                  │
│    - source.type: INFERRED (marks as AI-generated)                      │
│    - customProperties.assertionTriggers: "ON_INGESTION,ON_PROFILE"      │
│    - Linked to dataset URN                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                 Ingestion or profiling occurs for dataset
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    INGESTION SOURCE MAPPER ACTION                        │
│                                                                          │
│  • Listens to: MetadataChangeLog events                                 │
│  • Captures: pipelineName from system metadata                          │
│  • Stores: datasetProperties.customProperties["datahub.ingestion.       │
│             sourceUrn"] = "urn:li:dataHubIngestionSource:abc123"        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                 Dataset → Source mapping now available
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    ASSERTION EXECUTOR ACTION                             │
│                                                                          │
│  1. Listens to:                                                          │
│     - status aspect (ON_INGESTION trigger)                              │
│     - datasetProfile aspect (ON_PROFILE trigger)                        │
│                                                                          │
│  2. When event received:                                                 │
│     - Query all assertions for dataset                                   │
│     - Filter by trigger type                                             │
│     - For each matching assertion:                                       │
│                                                                          │
│  3. Execute assertion:                                                   │
│     - Use ConnectorRegistry.find_ingestion_source_for_dataset()         │
│     - Get DB connection using source credentials                         │
│     - Execute SQL query                                                  │
│     - Evaluate result against assertion parameters                       │
│                                                                          │
│  4. Emit results:                                                        │
│     - Create AssertionRunEvent with pass/fail status                    │
│     - Include actual values and error messages                          │
│     - Emit to DataHub as timeseries data                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                 Results visible in DataHub UI
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER VIEWS RESULTS                              │
│                                                                          │
│  • Governance/Validation tab shows assertion results                     │
│  • Pass/fail status visible                                              │
│  • Actual values and error messages displayed                           │
│  • Historical trends available (timeseries)                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components Implemented

### 1. Ingestion Source Mapper Action

**Purpose**: Creates durable mapping between datasets and their ingestion sources

**Location**: `datahub-actions/src/datahub_actions/plugin/action/ingestion_source_mapper/`

**How it works**:
- Listens to all dataset MetadataChangeLog events
- Extracts `pipelineName` from system metadata
- Stores in `DatasetProperties.customProperties["datahub.ingestion.sourceUrn"]`
- Now every dataset knows which connector ingested it

**Configuration**: `ingestion-source-mapper-action-config.yaml`

---

### 2. Assertion Executor Action

**Purpose**: Automatically executes SQL assertions using the correct connector

**Location**: `datahub-actions/src/datahub_actions/plugin/action/assertion_executor/`

**How it works**:
1. Listens to dataset events:
   - `status` aspect changes (ingestion events)
   - `datasetProfile` aspect changes (profiling events)

2. Queries assertions for the dataset via GraphQL

3. Filters assertions by trigger type:
   - Checks `customProperties.assertionTriggers`
   - Defaults to `ON_INGESTION` for `source.type = INFERRED` assertions

4. Executes SQL assertions:
   - Uses `ConnectorRegistry.find_ingestion_source_for_dataset()` to find source
   - Gets database connection with source's credentials
   - Executes SQL query
   - Evaluates result against assertion parameters

5. Emits `AssertionRunEvent` with results

**Configuration**: `assertion-executor-action-config.yaml`

---

## Frontend Integration

### Step 1: AI Assistant Generates SQL

**Current State**: ✅ Working (validation and SQL generation complete)

The AI assistant already:
- Validates that the quality rule is feasible
- Generates SQL query for the check

### Step 2: Persist Assertion via GraphQL

**Required**: Call `upsertCustomAssertion` mutation

**Example Mutation**:

```graphql
mutation upsertCustomAssertion($input: UpsertCustomAssertionInput!) {
  upsertCustomAssertion(input: $input) {
    urn
  }
}
```

**Input Variables**:

```javascript
{
  "input": {
    "entityUrn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,db.schema.table,PROD)",
    "type": "SQL",
    "description": "AI-generated: Check that active user count is greater than 1000",
    "platform": {
      "urn": "urn:li:dataPlatform:snowflake"
    },
    "source": {
      "type": "INFERRED"  // Marks as AI-generated
    },
    "sqlAssertion": {
      "type": "METRIC",  // or "METRIC_CHANGE"
      "statement": "SELECT COUNT(*) FROM users WHERE status = 'active'",
      "operator": "GREATER_THAN",
      "parameters": {
        "value": {
          "value": "1000",
          "type": "NUMBER"
        }
      }
    },
    "customProperties": [
      {
        "key": "assertionTriggers",
        "value": "ON_INGESTION,ON_PROFILE"  // When to execute
      },
      {
        "key": "aiGenerated",
        "value": "true"
      },
      {
        "key": "generatedAt",
        "value": "2025-11-07T10:30:00Z"
      }
    ]
  }
}
```

### Step 3: Frontend Implementation

**Location**: `datahub-web-react/src/app/entityV2/shared/tabs/Dataset/validations/`

**Required Changes**:

1. **After SQL generation**, call the GraphQL mutation:

```typescript
import { useMutation } from '@apollo/client';

const UPSERT_CUSTOM_ASSERTION = gql`
  mutation upsertCustomAssertion($input: UpsertCustomAssertionInput!) {
    upsertCustomAssertion(input: $input) {
      urn
    }
  }
`;

function AIAssistantComponent({ datasetUrn }: Props) {
  const [upsertAssertion] = useMutation(UPSERT_CUSTOM_ASSERTION);

  const handleSaveAssertion = async (
    sqlQuery: string,
    operator: string,
    threshold: string,
    description: string
  ) => {
    try {
      const result = await upsertAssertion({
        variables: {
          input: {
            entityUrn: datasetUrn,
            type: "SQL",
            description: `AI-generated: ${description}`,
            platform: {
              urn: extractPlatformUrn(datasetUrn)  // Extract from dataset URN
            },
            source: {
              type: "INFERRED"  // Mark as AI-generated
            },
            sqlAssertion: {
              type: "METRIC",
              statement: sqlQuery,
              operator: operator,  // e.g., "GREATER_THAN", "BETWEEN", "EQUAL_TO"
              parameters: buildParameters(operator, threshold)
            },
            customProperties: [
              {
                key: "assertionTriggers",
                value: "ON_INGESTION,ON_PROFILE"
              },
              {
                key: "aiGenerated",
                value: "true"
              },
              {
                key: "generatedAt",
                value: new Date().toISOString()
              }
            ]
          }
        }
      });

      // Show success message
      notification.success({
        message: 'Assertion Created',
        description: 'Custom quality check will run on every ingestion'
      });

      return result.data.upsertCustomAssertion.urn;
    } catch (error) {
      notification.error({
        message: 'Failed to Create Assertion',
        description: error.message
      });
    }
  };

  // Helper to build parameters based on operator
  const buildParameters = (operator: string, threshold: string) => {
    if (operator === "BETWEEN") {
      const [min, max] = threshold.split(",");
      return {
        minValue: { value: min.trim(), type: "NUMBER" },
        maxValue: { value: max.trim(), type: "NUMBER" }
      };
    } else {
      return {
        value: { value: threshold, type: "NUMBER" }
      };
    }
  };
}
```

2. **Operator Mapping**:

| SQL Condition | Operator Value | Parameters |
|---------------|----------------|------------|
| `value > 100` | `GREATER_THAN` | `value: { value: "100", type: "NUMBER" }` |
| `value >= 100` | `GREATER_THAN_OR_EQUAL_TO` | `value: { value: "100", type: "NUMBER" }` |
| `value < 100` | `LESS_THAN` | `value: { value: "100", type: "NUMBER" }` |
| `value <= 100` | `LESS_THAN_OR_EQUAL_TO` | `value: { value: "100", type: "NUMBER" }` |
| `value = 100` | `EQUAL_TO` | `value: { value: "100", type: "NUMBER" }` |
| `value BETWEEN 10 AND 100` | `BETWEEN` | `minValue: { value: "10", type: "NUMBER" }`, `maxValue: { value: "100", type: "NUMBER" }` |

---

## Testing the Implementation

### Step 1: Deploy Updated DataHub Actions

1. **Rebuild datahub-actions image** (if using custom image):
   ```bash
   cd datahub-actions
   docker build -t ghcr.io/starschema/datahub-actions-with-governance:latest .
   docker push ghcr.io/starschema/datahub-actions-with-governance:latest
   ```

2. **Restart datahub-actions container**:
   ```bash
   docker compose -f datahub-with-data-quality.yml restart datahub-actions
   ```

3. **Verify actions are loaded**:
   ```bash
   docker logs datahub-datahub-actions-1 -f | grep -i "assertion_executor\|ingestion_source_mapper"
   ```

   You should see:
   ```
   Action Pipeline with name 'ingestion_source_mapper' is now running
   Action Pipeline with name 'assertion_executor' is now running
   ```

### Step 2: Create Test Assertion via AI Assistant

1. Navigate to a Snowflake dataset in DataHub UI
2. Open AI Assistant in Validations tab
3. Enter a custom quality check (e.g., "Row count should be greater than 1000")
4. AI validates and generates SQL
5. Click "Save as Assertion"
6. Frontend calls `upsertCustomAssertion` mutation

### Step 3: Trigger Assertion Execution

**Option A: Run Ingestion**
```bash
datahub ingest -c snowflake_ingestion.yml
```

**Option B: Manually Trigger (for testing)**
```python
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import StatusClass

emitter = DatahubRestEmitter("http://localhost:8080")

dataset_urn = make_dataset_urn(
    platform="snowflake",
    name="db.schema.table",
    env="PROD"
)

# Emit status aspect to trigger ON_INGESTION assertions
status = StatusClass(removed=False)
mcp = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=status
)

emitter.emit(mcp)
```

### Step 4: Verify Assertion Execution

1. **Check logs**:
   ```bash
   docker logs datahub-datahub-actions-1 -f | grep -i "assertion"
   ```

   Expected output:
   ```
   Processing ingestion event for: urn:li:dataset:...
   Found 1 assertions for urn:li:dataset:..., filtering by trigger type: ON_INGESTION
   Executing 1 assertions for urn:li:dataset:...
   Executing SQL assertion urn:li:assertion:... for urn:li:dataset:...
   SQL query returned result: 1523
   Assertion urn:li:assertion:... PASSED: actual=1523
   Emitted assertion result for urn:li:assertion:...
   ```

2. **Check UI**:
   - Navigate to dataset in DataHub
   - Open Governance/Validation tab
   - Should see assertion with pass/fail status
   - Actual values displayed
   - Historical results available

3. **Query via GraphQL**:
   ```graphql
   query {
     dataset(urn: "urn:li:dataset:...") {
       assertions(start: 0, count: 10) {
         assertions {
           urn
           info {
             type
             description
             source {
               type
             }
           }
           runEvents(start: 0, count: 10) {
             total
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

## Trigger Configuration

Assertions can have different trigger types configured via `customProperties.assertionTriggers`:

| Trigger Type | When Executed | Use Case |
|--------------|---------------|----------|
| `ON_INGESTION` | Every time dataset is ingested (status aspect changes) | Most common - runs on every ingestion |
| `ON_PROFILE` | When dataset is profiled (datasetProfile aspect changes) | Use cached profile data for checks |
| `ON_INGESTION,ON_PROFILE` | Both ingestion and profiling | Run on any dataset update |

**Default**: If no `assertionTriggers` is specified, AI-generated assertions (source.type = INFERRED) default to `ON_INGESTION`.

---

## Connector Support

The implementation reuses existing ingestion source configurations for zero-duplication:

### Currently Supported Platforms
- ✅ Snowflake (native connection support)
- ✅ PostgreSQL (SQLAlchemy)
- ✅ MySQL (SQLAlchemy)

### To Add New Platform Support

1. **Extend ConnectorRegistry** (`datahub-actions/.../data_quality/connector_registry.py`):
   ```python
   elif platform == "bigquery":
       from datahub.ingestion.source.sql.bigquery import BigQueryConfig
       resolved_config = self._resolve_secrets(source_config)
       bq_config = BigQueryConfig.parse_obj(resolved_config)
       connection_string = bq_config.get_sql_alchemy_url()
   ```

2. **No credential duplication needed** - uses DataHub's encrypted secret store

---

## Security Considerations

### Credential Management
- ✅ Uses existing ingestion source credentials (zero duplication)
- ✅ Secrets resolved from DataHub's encrypted secret store
- ✅ No credentials stored in assertion definitions
- ✅ Connector discovery automatic via DataHub GraphQL

### SQL Injection Protection
- ⚠️ SQL statements are executed as-is from assertions
- 🔒 **Recommendation**: Add SQL validation/sanitization in AI assistant
- 🔒 **Recommendation**: Restrict assertion creation to authorized users
- 🔒 **Recommendation**: Use read-only database accounts for quality checks

### Access Control
- Assertions inherit permissions from parent dataset
- Only users with edit permissions on dataset can create assertions
- Assertion execution uses system-level access (datahub-actions service account)

---

## Troubleshooting

### Assertion Not Executing

1. **Check if action is running**:
   ```bash
   docker logs datahub-datahub-actions-1 | grep "assertion_executor"
   ```

2. **Check trigger configuration**:
   - Verify `customProperties.assertionTriggers` is set
   - Verify ingestion emits `status` aspect
   - Check action config has `trigger_on_ingestion: true`

3. **Check dataset→source mapping**:
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
   Should include `datahub.ingestion.sourceUrn`

### Connector Not Found

1. **Verify ingestion source exists in DataHub**:
   ```graphql
   query {
     listIngestionSources(input: { start: 0, count: 100 }) {
       total
       ingestionSources {
         urn
         name
         type
       }
     }
   }
   ```

2. **Check ConnectorRegistry logs**:
   ```bash
   docker logs datahub-datahub-actions-1 | grep "ConnectorRegistry"
   ```

### SQL Execution Fails

1. **Check connection**:
   - Verify ingestion source credentials are valid
   - Test connection manually

2. **Check SQL syntax**:
   - Verify SQL is valid for the platform
   - Test query directly in database

3. **Check permissions**:
   - Ensure ingestion source account has SELECT permissions
   - Check table/schema access

---

## Next Steps

### Phase 5: GraphQL Schema Extension (Optional)

If you want typed GraphQL support for AI-generated assertions, extend:

**File**: `datahub-graphql-core/src/main/resources/assertion.graphql`

```graphql
input UpsertCustomAssertionInput {
  # ... existing fields ...

  sqlAssertion: SqlAssertionInput  # Add this if not present

  source: AssertionSourceInput  # Add this if not present
}

input SqlAssertionInput {
  type: SqlAssertionType!
  statement: String!
  operator: AssertionStdOperator!
  parameters: AssertionStdParametersInput
}

input AssertionSourceInput {
  type: AssertionSourceType!
}

enum AssertionSourceType {
  NATIVE
  EXTERNAL
  INFERRED  # AI-generated
}
```

### Phase 6: UI Enhancements

1. **Assertion List View**:
   - Filter by source type (show only AI-generated)
   - Edit/delete assertions
   - Re-run assertion manually

2. **Historical Trends**:
   - Chart showing assertion results over time
   - Alert on failures

3. **Trigger Configuration UI**:
   - Let users choose when to run assertion
   - Show last execution time

---

## Summary

### What's Working Now

✅ Dataset → Source mapping (automatic)
✅ Assertion storage with SQL, operators, parameters
✅ Automatic execution on ingestion/profiling
✅ Correct connector discovery and credentials
✅ Result emission as AssertionRunEvent
✅ Multi-trigger support (ON_INGESTION, ON_PROFILE)

### What Frontend Needs to Do

1. Call `upsertCustomAssertion` GraphQL mutation after SQL generation
2. Pass SQL query, operator, threshold, and description
3. Mark assertion as AI-generated (source.type = INFERRED)
4. Set trigger type in customProperties

### Deployment

1. Restart datahub-actions with new configs
2. Verify both actions are running
3. Create test assertion via AI assistant
4. Run ingestion to trigger execution
5. Check results in UI

**Status**: Backend implementation complete and ready for frontend integration!
