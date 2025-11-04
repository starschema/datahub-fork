# DataHub Governance Bot

Real-time governance enforcement for DataHub using event-driven automation.

## Overview

The Governance Bot monitors entity changes in DataHub and automatically:

- ✅ **Validates compliance** against configurable governance rules
- 📊 **Updates UI** with pass/fail status in the Governance tab
- 🚨 **Creates incidents** for critical violations (optional)
- 🔄 **Auto-resolves** incidents when violations are fixed
- ⚡ **Real-time** governance checks within seconds of metadata changes

## Features

### Governance Checks

- **Ownership**: Require minimum number of owners with specific types
- **Description**: Enforce non-empty descriptions with minimum length
- **Glossary Terms**: Require classification terms (PII, Financial, etc.)
- **Tags**: Require compliance or categorization tags

### Rule Scoping

Filter which entities rules apply to:
- Entity types (DATASET, DASHBOARD, CHART, DATA_JOB)
- Platforms (snowflake, bigquery, dbt, etc.)
- Environments (PROD, DEV, QA)
- Tags (tier:1, PII, etc.)
- Domains

### Output Options

- **TestResults Aspect**: Results appear in Governance tab automatically
- **Incidents**: Track violations with priority, assignees, and lifecycle
- **Auto-Resolution**: Incidents resolved when checks pass

## Architecture

```
Entity Change Event → Governance Action → Rules Engine → Dual Output
                            ↓                  ↓              ↓
                      GraphQL Fetch      Evaluate        TestResults
                      (ownership,        Checks          (UI visibility)
                       tags, terms)                          +
                                                         Incidents
                                                       (Optional tracking)
```

## Quick Start

### 1. Configure Rules

Create `governance_rules.yml`:

```yaml
rules:
  - name: tier1_governance
    enabled: true

    scope:
      entity_types: [DATASET]
      platforms: [snowflake]
      tags_any: ["urn:li:tag:tier:1"]
      envs: [PROD]

    checks:
      - type: requires_owner
        params:
          min_owners: 2
          allowed_types: [DATAOWNER, TECHNICAL_OWNER]

      - type: requires_description
        params:
          min_length: 50

      - type: requires_glossary_term
        params:
          any_of:
            - "urn:li:glossaryTerm:Classification.PII"
            - "urn:li:glossaryTerm:Classification.Financial"

    emit_test_results: true
    create_incident_on_fail: true

    incident_config:
      priority: HIGH
      custom_type: "GOVERNANCE_VIOLATION"
      assignees:
        - "urn:li:corpGroup:data-governance-team"
```

### 2. Configure Action

Create `action_config.yml`:

```yaml
name: "governance_bot"
enabled: true

source:
  type: "kafka"
  config:
    connection:
      bootstrap: "${KAFKA_BOOTSTRAP_SERVER:-localhost:9092}"
      schema_registry_url: "${SCHEMA_REGISTRY_URL:-http://localhost:8081}"

action:
  type: "governance"
  config:
    enabled: true
    rules_file: "./governance_rules.yml"

datahub:
  server: "${DATAHUB_GMS_URL:-http://localhost:8080}"
  token: "${DATAHUB_SYSTEM_CLIENT_SECRET}"
```

### 3. Deploy Action

```bash
# Run with datahub-actions CLI
datahub-actions -c action_config.yml

# Or use Docker
docker run -v $(pwd)/action_config.yml:/etc/datahub/actions/config.yml \
  -v $(pwd)/governance_rules.yml:/etc/datahub/actions/governance_rules.yml \
  acryldata/datahub-actions:latest
```

## Rule Configuration Reference

### Scope Configuration

```yaml
scope:
  entity_types: [DATASET, DASHBOARD, CHART, DATA_JOB]
  platforms: [snowflake, bigquery, dbt]
  envs: [PROD, DEV, QA]
  tags_any: ["urn:li:tag:tier:1", "urn:li:tag:PII"]
  domains: ["urn:li:domain:Finance"]
```

All scope filters are optional. If specified:
- `entity_types`: Entity must match one of these types
- `platforms`: Entity must be on one of these platforms
- `envs`: Entity must be in one of these environments
- `tags_any`: Entity must have at least one of these tags
- `domains`: Entity must be in one of these domains

### Check Types

#### requires_owner

Validates entity has sufficient ownership.

```yaml
- type: requires_owner
  params:
    min_owners: 2                    # Minimum number of owners (default: 1)
    allowed_types:                   # Optional: filter by owner type
      - DATAOWNER
      - TECHNICAL_OWNER
      - BUSINESS_OWNER
```

#### requires_description

Validates entity has a description.

```yaml
- type: requires_description
  params:
    min_length: 50                   # Minimum description length (default: 1)
```

Checks in order:
1. `editableProperties.description` (user-editable)
2. `properties.description` (platform-provided)
3. `institutionalMemory` (documentation links)

#### requires_glossary_term

Validates entity has required glossary terms.

```yaml
- type: requires_glossary_term
  params:
    any_of:                          # Entity must have at least one of these
      - "urn:li:glossaryTerm:Classification.PII"
      - "urn:li:glossaryTerm:Classification.Financial"

    # OR

    all_of:                          # Entity must have all of these
      - "urn:li:glossaryTerm:DataQuality.Validated"
      - "urn:li:glossaryTerm:Compliance.GDPR"
```

#### requires_tag

Validates entity has required tags.

```yaml
- type: requires_tag
  params:
    any_of:                          # Entity must have at least one of these
      - "urn:li:tag:GDPR"
      - "urn:li:tag:CCPA"

    # OR

    all_of:                          # Entity must have all of these
      - "urn:li:tag:Validated"
      - "urn:li:tag:Production"
```

### Incident Configuration

```yaml
emit_test_results: true              # Always show in Governance tab (default: true)
create_incident_on_fail: true        # Create incidents for failures (default: false)

incident_config:
  priority: HIGH                     # LOW, MEDIUM, HIGH, CRITICAL
  custom_type: "GOVERNANCE_VIOLATION" # Custom incident type for filtering
  assignees:
    - "urn:li:corpuser:jdoe"
    - "urn:li:corpGroup:governance-team"
```

## How It Works

### Event Flow

1. **Entity Change**: Metadata updated in DataHub
2. **Event Published**: Kafka MCL (Metadata Change Log) event emitted
3. **Action Triggered**: Governance bot receives event
4. **Metadata Fetch**: GraphQL query for ownership, tags, terms
5. **Rule Evaluation**: Check if entity matches scope → run checks
6. **Emit Results**:
   - TestResults aspect → Governance tab
   - Incidents (if configured) → Incident tracking

### UI Integration

Governance results appear in **two places**:

#### 1. Governance Tab (TestResults)

- Automatically shows pass/fail status for each check
- Green checkmarks for passing checks
- Red X for failing checks
- Accessible at: `https://your-datahub.com/dataset/<urn>?tab=Governance`

#### 2. Incidents (Optional)

- Created for critical violations
- Trackable with priority and assignees
- Auto-resolve when violations fixed
- Accessible at: `https://your-datahub.com/dataset/<urn>?tab=Incidents`

## Testing

### Run Unit Tests

```bash
pytest tests/unit/governance/
```

### Manual Testing

1. **Start DataHub**:
   ```bash
   ./gradlew quickstartDebug
   ```

2. **Deploy Governance Action**:
   ```bash
   datahub-actions -c examples/governance/action_config.yml
   ```

3. **Create Test Dataset**:
   ```python
   from datahub.emitter.mce_builder import make_dataset_urn
   from datahub.emitter.rest_emitter import DatahubRestEmitter

   emitter = DatahubRestEmitter("http://localhost:8080")
   dataset_urn = make_dataset_urn("snowflake", "db.schema.test_table", "PROD")

   # Add tier:1 tag to trigger tier1_governance rule
   # ... (see DataHub SDK docs)
   ```

4. **Check Governance Tab**: Navigate to dataset in UI → Governance tab

5. **Verify Results**: Should see governance check results

## Troubleshooting

### No results in Governance tab

- **Check logs**: `datahub-actions` should show "Processing entity for governance checks"
- **Verify scope**: Entity might not match rule scope (check entity_types, platforms, tags)
- **Check GraphQL**: Ensure metadata fetch is successful (ownership, tags, terms exist)

### Incidents not created

- **Verify config**: `create_incident_on_fail: true` and `incident_config` present
- **Check permissions**: DataHub token needs incident creation permissions
- **Review logs**: Look for "Created incident" or error messages

### Tests failing

- **Missing owners**: Add ownership to test entity
- **No tags**: Add required tags to match scope
- **Platform mismatch**: Ensure platform in scope matches entity platform

## Extending

### Add Custom Check

1. **Create check class**:

```python
# checks/custom.py
from datahub_actions.plugin.action.governance.checks.base import BaseGovernanceCheck

class CustomCheck(BaseGovernanceCheck):
    @property
    def check_type(self) -> str:
        return "my_custom_check"

    def evaluate(self, entity_urn, metadata, params):
        # Your custom logic here
        passed = some_condition(metadata)
        return self._create_result(
            check_name="custom_check",
            passed=passed,
            message="Check result message"
        )
```

2. **Register in rules_engine.py**:

```python
CHECK_REGISTRY = {
    # ... existing checks
    "my_custom_check": CustomCheck,
}
```

3. **Use in rules**:

```yaml
checks:
  - type: my_custom_check
    params:
      custom_param: value
```

## Production Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datahub-governance-bot
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: governance-action
        image: acryldata/datahub-actions:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVER
          value: "kafka:9092"
        - name: DATAHUB_GMS_URL
          value: "http://datahub-gms:8080"
        - name: DATAHUB_SYSTEM_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: datahub-secrets
              key: system-client-secret
        volumeMounts:
        - name: config
          mountPath: /etc/datahub/actions
      volumes:
      - name: config
        configMap:
          name: governance-config
```

### Monitoring

Key metrics to monitor:
- Event processing rate
- Rule evaluation latency
- Check pass/fail rates
- Incident creation rate

## Resources

- [DataHub Actions Documentation](https://datahubproject.io/docs/actions/)
- [DataHub GraphQL API](https://datahubproject.io/docs/graphql/overview)
- [DataHub Tests & Assertions](https://datahubproject.io/docs/tests/)
- [DataHub Incidents](https://datahubproject.io/docs/incidents/)

## Support

- GitHub Issues: https://github.com/datahub-project/datahub/issues
- Slack: https://datahubspace.slack.com

## License

Apache License 2.0
