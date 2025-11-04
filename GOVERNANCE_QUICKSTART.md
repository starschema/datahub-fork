# DataHub Governance Bot - Quick Start Guide

This guide walks you through testing and deploying the DataHub Governance Bot with your existing Docker Compose setup.

## 📋 Prerequisites

- Docker and Docker Compose installed
- DataHub environment running from `datahub-with-data-quality.yml`
- Python 3.9+ (for local development/testing)

## 🚀 Quick Start

### Step 1: Start DataHub with Governance Bot

```bash
# Navigate to datahub directory
cd /path/to/datahub

# Start all services including governance bot
docker compose -f datahub-with-data-quality.yml up -d

# Check that governance action is running
docker compose -f datahub-with-data-quality.yml logs -f datahub-actions
```

You should see logs indicating the governance action has started:
```
Governance Action configured with rules file: /etc/datahub/actions/conf/governance-rules.yml
GovernanceAction initialized with 5 rules
```

### Step 2: Access DataHub UI

1. Open your browser: http://localhost:9002
2. Login with default credentials:
   - Username: `datahub`
   - Password: `datahub`

### Step 3: Create a Test Dataset

#### Option A: Using Python SDK

```python
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    ChangeTypeClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
)

# Initialize emitter
emitter = DatahubRestEmitter("http://localhost:8080")

# Create a test dataset URN
dataset_urn = make_dataset_urn("snowflake", "test_db.test_schema.governance_test", "PROD")

# Add an owner (this should make the ownership check pass)
ownership = OwnershipClass(
    owners=[
        OwnerClass(
            owner="urn:li:corpuser:datahub",
            type=OwnershipTypeClass.DATAOWNER,
        )
    ]
)

# Emit ownership
from datahub.metadata.schema_classes import MetadataChangeProposalWrapper
proposal = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=ownership,
)
emitter.emit(proposal)

print(f"✅ Created test dataset: {dataset_urn}")
print("🔍 Check the Governance tab in DataHub UI!")
```

#### Option B: Using DataHub CLI

```bash
# Install DataHub CLI if not already installed
pip install 'acryl-datahub'

# Ingest a sample dataset
datahub ingest -c sample-data-config.yml
```

### Step 4: View Governance Results

1. Navigate to your dataset in DataHub UI
2. Click the **"Governance"** tab
3. You should see:
   - ✅ Green checkmarks for passed checks
   - ❌ Red X marks for failed checks
   - Details about each governance rule

Example results:
```
✅ production_dataset_governance
   ✅ requires_owner: Found 1 valid owner(s)
   ❌ requires_description: No description found

❌ snowflake_production_governance
   ✅ requires_owner: Found 1 valid owner(s)
   ❌ requires_description: Description too short (0 characters, required: 10)
```

## 🧪 Testing Different Governance Scenarios

### Test 1: Missing Owner (Should Fail)

Create a dataset without an owner:

```python
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import DatasetPropertiesClass

emitter = DatahubRestEmitter("http://localhost:8080")
dataset_urn = make_dataset_urn("snowflake", "test_db.test_schema.no_owner", "PROD")

properties = DatasetPropertiesClass(
    description="Test dataset with no owner"
)

from datahub.metadata.schema_classes import MetadataChangeProposalWrapper
proposal = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=properties,
)
emitter.emit(proposal)
```

**Expected Result**: Governance tab shows failed `requires_owner` check

### Test 2: Tier 1 Dataset (Strict Governance)

Create a dataset with the `tier:1` tag:

```python
from datahub.metadata.schema_classes import GlobalTagsClass, TagAssociationClass

dataset_urn = make_dataset_urn("snowflake", "test_db.test_schema.tier1_data", "PROD")

# Add tier:1 tag
tags = GlobalTagsClass(
    tags=[
        TagAssociationClass(tag="urn:li:tag:tier:1")
    ]
)

proposal = MetadataChangeProposalWrapper(
    entityUrn=dataset_urn,
    aspect=tags,
)
emitter.emit(proposal)
```

**Expected Result**:
- `tier1_governance` rule triggers
- Requires 2 owners (will fail with only 1)
- Requires description (min 50 characters)
- Requires classification term

### Test 3: PII Dataset (Critical Governance)

```python
from datahub.metadata.schema_classes import GlossaryTermsClass, GlossaryTermAssociationClass

dataset_urn = make_dataset_urn("snowflake", "test_db.test_schema.pii_data", "PROD")

# Add PII tag
tags = GlobalTagsClass(
    tags=[
        TagAssociationClass(tag="urn:li:tag:PII")
    ]
)
emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=tags))

# Add PII classification term
terms = GlossaryTermsClass(
    terms=[
        GlossaryTermAssociationClass(urn="urn:li:glossaryTerm:Classification.PII")
    ]
)
emitter.emit(MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=terms))
```

**Expected Result**:
- `pii_data_governance` rule triggers
- Creates CRITICAL priority incident if compliance tags missing
- Incident assigned to privacy-team

## 📊 Monitoring Governance

### View Governance Action Logs

```bash
# Follow governance action logs
docker compose -f datahub-with-data-quality.yml logs -f datahub-actions | grep -i governance

# Check for rule evaluations
docker compose -f datahub-with-data-quality.yml logs datahub-actions | grep "Governance evaluation"
```

Expected log output:
```
Processing entity for governance checks: urn:li:dataset:...
Rule 'production_dataset_governance' evaluation: PASSED (2 checks)
Emitted TestResults for urn:li:dataset:...: 1 passing, 1 failing
```

### View Incidents

1. Navigate to DataHub UI
2. Go to entity → **Incidents** tab
3. See active incidents for governance violations
4. Incidents will auto-resolve when violations are fixed

## ⚙️ Customizing Governance Rules

Edit `governance-rules.yml` to customize your governance requirements:

```yaml
rules:
  # Add your custom rule
  - name: my_custom_rule
    enabled: true

    scope:
      entity_types: [DATASET]
      platforms: [bigquery]

    checks:
      - type: requires_owner
        params:
          min_owners: 1

    emit_test_results: true
    create_incident_on_fail: false
```

After editing, restart the datahub-actions container:

```bash
docker compose -f datahub-with-data-quality.yml restart datahub-actions
```

## 🔧 Troubleshooting

### Governance results not showing in UI

**Issue**: Governance tab shows no results

**Solutions**:
1. Check that metadata change event was emitted:
   ```bash
   docker compose logs datahub-actions | grep "Processing entity"
   ```

2. Verify entity matches rule scope:
   ```bash
   docker compose logs datahub-actions | grep "not in scope"
   ```

3. Check GraphQL metadata fetch succeeded:
   ```bash
   docker compose logs datahub-actions | grep "Could not fetch metadata"
   ```

### Action not starting

**Issue**: Governance action fails to start

**Solutions**:
1. Check configuration file is mounted:
   ```bash
   docker compose exec datahub-actions ls -la /etc/datahub/actions/conf/
   ```

2. Verify YAML syntax:
   ```bash
   docker compose exec datahub-actions python -c "import yaml; yaml.safe_load(open('/etc/datahub/actions/conf/governance-rules.yml'))"
   ```

3. Check action logs for errors:
   ```bash
   docker compose logs datahub-actions | grep -i error
   ```

### Rules not being evaluated

**Issue**: No governance checks running

**Solutions**:
1. Verify rule is enabled in `governance-rules.yml`:
   ```yaml
   - name: my_rule
     enabled: true  # Make sure this is true
   ```

2. Check entity matches scope filters:
   - Entity type must match `entity_types`
   - Platform must match `platforms`
   - Tags must match `tags_any`

3. View detailed logs:
   ```bash
   docker compose logs datahub-actions | grep "matches_scope"
   ```

## 🎯 Next Steps

1. **Add Glossary Terms**: Create classification terms in DataHub UI
   - Go to Governance → Glossary
   - Create terms like `Classification.PII`, `Classification.Financial`

2. **Create Tags**: Add custom tags for governance
   - Go to Tags
   - Create tags like `tier:1`, `Sensitive`, `GDPR`

3. **Set Up Owners**: Assign ownership to datasets
   - Add users to corp groups
   - Assign ownership in dataset UI or via API

4. **Monitor Incidents**: Review governance violations
   - Set up incident notifications
   - Assign incidents to teams
   - Track resolution progress

5. **Customize Rules**: Tailor governance to your organization
   - Add platform-specific rules
   - Define domain-specific checks
   - Set appropriate incident priorities

## 📚 Additional Resources

- **Governance Plugin README**: `datahub-actions/src/datahub_actions/plugin/action/governance/README.md`
- **Example Rules**: `datahub-actions/examples/governance/rules.yml`
- **DataHub Docs**: https://datahubproject.io/docs/
- **GraphQL API**: https://datahubproject.io/docs/graphql/overview

## 🐛 Getting Help

If you encounter issues:

1. Check logs: `docker compose -f datahub-with-data-quality.yml logs datahub-actions`
2. Review configuration files for YAML syntax errors
3. Verify DataHub is running: `docker compose ps`
4. Check DataHub health: http://localhost:8080/health

---

**Happy Governing! 🎉**
