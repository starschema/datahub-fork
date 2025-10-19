# Query-Based Quality Tests - Quick Setup Guide

## TL;DR - 5 Minute Setup

Get all 20 data quality test types (profile + query-based) working in 5 minutes!

## Prerequisites

- ✅ DataHub running with Actions framework
- ✅ Snowflake (or other DB) with read access credentials
- ✅ Docker image `my-datahub-actions:latest` built

## Step 1: Configure Database Credentials (2 minutes)

Edit `data-quality-action-config.yaml` and update the Snowflake connector:

```yaml
connectors:
  snowflake:
    # Replace with YOUR actual credentials
    connection_string: "snowflake://YOUR_USER:YOUR_PASSWORD@YOUR_ACCOUNT/?warehouse=YOUR_WAREHOUSE&role=YOUR_ROLE"
```

**Format Guide:**
```
snowflake://USERNAME:PASSWORD@ACCOUNT_ID/DATABASE?warehouse=WAREHOUSE&role=ROLE

Examples:
- snowflake://datahub_ro:SecurePass123@xy12345.us-east-1/PROD_DB?warehouse=COMPUTE_WH&role=ANALYST
- snowflake://reader:MyP@ssw0rd@ab67890.us-west-2/?warehouse=WH_SMALL&role=READ_ONLY
```

**Security Note:** This file contains credentials - add to `.gitignore`!

## Step 2: Verify Test Configuration (1 minute)

The config already has 18 tests configured (13 profile + 5 query-based).

**Query-based tests that will run:**
1. ✅ `fips_code_length_check` - Validates FIPS codes are 5 characters
2. ✅ `valid_state_abbreviations` - Ensures state codes are valid
3. ✅ `no_future_covid_dates` - No dates in the future
4. ✅ `covid_fips_exist_in_demographics` - Referential integrity
5. ✅ `no_negative_covid_cases` - No negative values

These tests **automatically execute SQL queries** using your Snowflake connection!

## Step 3: Update Docker Compose (1 minute)

Ensure `docker-compose-data-quality.override.yml` has:

```yaml
services:
  datahub-actions:
    image: my-datahub-actions:latest
    container_name: datahub-actions
    volumes:
      # Mount config with credentials
      - ./data-quality-action-config.yaml:/etc/datahub/actions/conf/data-quality.yaml:ro
    environment:
      - DATAHUB_GMS_HOST=datahub-gms
      - DATAHUB_GMS_PORT=8080
    depends_on:
      - datahub-gms
      - broker
    networks:
      - datahub_network
    restart: unless-stopped
```

## Step 4: Start DataHub Actions (1 minute)

```bash
# Start the actions container
docker-compose -f docker-compose-without-neo4j.yml \
  -f docker-compose-data-quality.override.yml \
  up -d datahub-actions

# Check it's running
docker ps | grep datahub-actions

# Watch logs
docker logs -f datahub-actions
```

**Look for:**
```
✓ Data Quality Action configured with 18 tests
✓ Using connector for platform: snowflake
✓ Executing data quality tests for dataset: urn:li:dataset:...
```

## Step 5: Trigger Quality Tests (immediate)

Run Snowflake ingestion with profiling:

```bash
datahub ingest -c your-snowflake-recipe.yml
```

**What happens automatically:**
1. Ingestion profiles datasets
2. Emits `datasetProfile` to Kafka
3. DataQualityAction auto-triggered
4. Runs **all 18 tests** (13 profile + 5 query-based)
5. Query-based tests execute SQL on Snowflake
6. All assertions emitted to DataHub

## Step 6: Verify in UI (1 minute)

1. Open DataHub UI: http://localhost:9002
2. Search for any Snowflake dataset (e.g., "demographics")
3. Click on dataset → **"Validations" tab**
4. See all assertions with pass/fail status!

**Expected Results:**
- Profile-based tests: ✅ (using cached data)
- Query-based tests: ✅ (executed fresh SQL)
- Total assertions: 10-15 per table (depends on columns)

## Verification Checklist

✅ **Config updated** with real Snowflake credentials
✅ **Docker container running** (`docker ps | grep datahub-actions`)
✅ **Logs show success** ("Data Quality Action configured")
✅ **Ingestion completed** with profiling enabled
✅ **Assertions visible** in UI Validations tab
✅ **Query-based tests passed** (check for SQL test names)
✅ **No credential leaks** in logs (`docker logs datahub-actions | grep -i password` finds nothing)

## Common Issues & Solutions

### Issue: "No connection config found for platform 'snowflake'"

**Solution:**
```yaml
# Make sure connector is configured:
connectors:
  snowflake:
    connection_string: "snowflake://..."  # Must be present!
```

### Issue: "Failed to connect to Snowflake"

**Possible causes:**
1. Incorrect credentials
2. Network issues (container can't reach Snowflake)
3. Account/warehouse/role typo

**Debug:**
```bash
# Test connection from container
docker exec -it datahub-actions bash
python -c "
from sqlalchemy import create_engine
engine = create_engine('snowflake://USER:PASS@ACCOUNT/?warehouse=WH&role=ROLE')
conn = engine.connect()
result = conn.execute('SELECT CURRENT_USER()').fetchone()
print(f'Connected as: {result[0]}')
"
```

### Issue: Query-based tests skipped

**Check:**
1. Is `connectors.snowflake.connection_string` configured?
2. Do test patterns match your dataset URNs?
3. Are columns referenced in tests actually present?

**View which tests matched:**
```bash
docker logs datahub-actions | grep "matches dataset"
```

### Issue: SQL query fails

**Common reasons:**
- Table name in SQL doesn't match actual table
- Column referenced doesn't exist
- Insufficient permissions (SELECT not granted)

**Check permissions:**
```sql
-- Snowflake
SHOW GRANTS TO ROLE your_role;

-- Should see USAGE on warehouse and SELECT on tables
```

## Testing Individual Components

### Test 1: Config Parsing

```bash
docker exec datahub-actions python -c "
import yaml
with open('/etc/datahub/actions/conf/data-quality.yaml') as f:
    config = yaml.safe_load(f)
print(f'Tests configured: {len(config[\"action\"][\"config\"][\"tests\"])}')
print(f'Connectors: {list(config[\"action\"][\"config\"][\"connectors\"].keys())}')
"
```

### Test 2: Database Connection

```bash
docker exec datahub-actions python -c "
from datahub_actions.plugin.action.data_quality.connector_registry import ConnectorRegistry

registry = ConnectorRegistry({
    'snowflake': {'connection_string': 'snowflake://USER:PASS@ACCOUNT/?warehouse=WH&role=ROLE'}
})

conn_str = registry.get_connection_string('urn:li:dataset:(urn:li:dataPlatform:snowflake,db.table,PROD)')
print(f'Connection resolved: {\"snowflake://\" in conn_str}')
"
```

### Test 3: Query Execution

```bash
docker exec datahub-actions python -c "
from sqlalchemy import create_engine

engine = create_engine('snowflake://USER:PASS@ACCOUNT/?warehouse=WH&role=ROLE')
with engine.connect() as conn:
    result = conn.execute('SELECT COUNT(*) FROM your_table').scalar()
    print(f'Query executed successfully: {result} rows')
"
```

## Next Steps

### Add More Tests

Edit `data-quality-action-config.yaml` and add tests:

```yaml
tests:
  # String validation
  - name: "email_format_valid"
    type: "column_values_match_regex"
    dataset_pattern: "urn:li:dataset:*snowflake*users*"
    column: "email"
    params:
      regex: "^[\\w._%+-]+@[\\w.-]+\\.[A-Za-z]{2,}$"

  # Set membership
  - name: "valid_country_codes"
    type: "column_values_in_set"
    dataset_pattern: "urn:li:dataset:*snowflake*customers*"
    column: "country"
    params:
      value_set: "US,CA,UK,DE,FR,JP"

  # Custom SQL
  - name: "no_orphan_orders"
    type: "table_custom_sql"
    dataset_pattern: "urn:li:dataset:*snowflake*orders*"
    params:
      sql: "SELECT COUNT(*) FROM orders o LEFT JOIN customers c ON o.customer_id = c.id WHERE c.id IS NULL"
      expected_result: "0"
```

### Add More Platforms

```yaml
connectors:
  postgres:
    connection_string: "postgresql://user:pass@localhost:5432/mydb"

  mysql:
    connection_string: "mysql://user:pass@localhost:3306/mydb"
```

Tests automatically work across all platforms!

### Schedule Regular Runs

Set up cron or Airflow to run ingestion regularly:

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/datahub && datahub ingest -c snowflake-recipe.yml
```

Quality tests run automatically each time!

## Support

**Documentation:**
- `QUERY_BASED_QUALITY_TESTS.md` - Complete architecture guide
- `DATA_QUALITY_SECURITY_GUIDE.md` - Security best practices
- `data-quality-action-config.TEMPLATE.yaml` - Clean config template

**Logs:**
```bash
# Follow real-time logs
docker logs -f datahub-actions

# Search for errors
docker logs datahub-actions 2>&1 | grep -i error

# Check specific dataset
docker logs datahub-actions 2>&1 | grep "urn:li:dataset:.*demographics"
```

## Success! 🎉

You now have:
- ✅ All 20 data quality test types working
- ✅ Automatic trigger on every ingestion
- ✅ Fresh SQL queries validating your data
- ✅ Secure credential management
- ✅ Results visible in DataHub UI

Quality tests will now run automatically every time you profile datasets!
