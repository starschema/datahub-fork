# DataHub Governance Rules Guide

## Overview

This guide documents the comprehensive governance rules implemented in DataHub, based on Acryl's best practices and production patterns. The system now includes **13 governance rules** covering critical data, compliance, production datasets, BI assets, data quality, pipelines, and development environments.

---

## 📊 Governance Rules Summary

### Rule Categories

| Category | Rules | Severity | Auto-Create Incidents |
|----------|-------|----------|---------------------|
| **Critical Data** | Tier 1 Governance | HIGH | ✅ Yes |
| **Compliance** | PII, Financial, Sensitive | CRITICAL/HIGH | ✅ Yes |
| **Production** | Standard, Snowflake, BigQuery | STANDARD | ❌ No |
| **BI & Analytics** | Dashboard, Chart | STANDARD | ❌ No |
| **Data Quality** | Certified Data | STANDARD | ❌ No |
| **Pipelines** | Critical Pipelines | MEDIUM | ✅ Yes |
| **Development** | Dev/QA/Staging | LIGHT | ❌ No |
| **Lifecycle** | Deprecated Assets | STANDARD | ❌ No |

---

## 🔴 Critical & Compliance Rules

### Rule 1: Tier 1 / Critical Data Governance (HIGH Priority)

**Purpose:** Strictest governance for mission-critical datasets

**Applies to:**
- Datasets in PROD environment
- Platforms: Snowflake, BigQuery, Postgres, Redshift
- Tagged with: `tier:1`, `Tier1`, or `Critical`

**Requirements:**
- ✅ **2+ owners** (DATAOWNER or TECHNICAL_OWNER)
- ✅ **100+ character description**
- ✅ **Classification glossary term** (one of):
  - PII, Sensitive, Financial, Public, or Internal
- ✅ **Validation tag** (one of):
  - Validated, Approved, or Certified

**Incidents:** Creates HIGH priority incidents assigned to data-governance-team

---

### Rule 2: PII Data Governance (CRITICAL Priority)

**Purpose:** Compliance requirements for personally identifiable information

**Applies to:**
- Datasets tagged with: `PII`, `PersonalData`, or `IdentifiableData`

**Requirements:**
- ✅ **1+ data owner**
- ✅ **50+ character description**
- ✅ **PII classification** glossary term
- ✅ **Compliance tag** (one of):
  - GDPR, CCPA, HIPAA, ComplianceReviewed, or AccessControlled

**Incidents:** Creates CRITICAL priority incidents assigned to privacy-team and data-governance-team

**Use Case:** Automatically enforced when datasets contain customer PII, email addresses, SSNs, etc.

---

### Rule 3: Financial Data Compliance (CRITICAL Priority)

**Purpose:** SOX and financial reporting data controls

**Applies to:**
- Datasets tagged with: `Financial`, `SOX`, or `FinancialReporting`

**Requirements:**
- ✅ **2+ data owners**
- ✅ **75+ character description**
- ✅ **Financial classification** glossary term
- ✅ **Compliance tag** (one of):
  - SOX, AuditReviewed, or ComplianceReviewed

**Incidents:** Creates CRITICAL priority incidents assigned to finance-team and compliance-team

**Use Case:** Revenue tables, financial statements, audit logs, accounting data

---

### Rule 4: Sensitive Data Governance (HIGH Priority)

**Purpose:** Proper classification for confidential business data

**Applies to:**
- Datasets tagged with: `Sensitive`, `Confidential`, or `Restricted`

**Requirements:**
- ✅ **1+ data owner**
- ✅ **50+ character description**
- ✅ **Sensitivity classification** glossary term
- ✅ **Access control tag** (one of):
  - AccessControlled, RestrictedUse, or ComplianceReviewed

**Incidents:** Creates HIGH priority incidents assigned to data-governance-team

**Use Case:** Proprietary algorithms, business strategies, employee data

---

## 🟢 Production Governance Rules

### Rule 5: Production Dataset Governance (STANDARD)

**Purpose:** Baseline governance for all production datasets

**Applies to:**
- All datasets in PROD environment
- **No platform restrictions** - applies universally

**Requirements:**
- ✅ **1+ owner** (any type)
- ✅ **20+ character description**

**Incidents:** None (informational only)

**Use Case:** Default baseline for all production data

---

### Rule 6: Snowflake Production Governance

**Purpose:** Platform-specific governance for Snowflake

**Applies to:**
- Snowflake datasets in PROD

**Requirements:**
- ✅ **1+ owner**
- ✅ **10+ character description** (lighter than general rule)

**Incidents:** None

---

### Rule 7: BigQuery Production Governance

**Purpose:** Platform-specific governance for BigQuery

**Applies to:**
- BigQuery datasets in PROD

**Requirements:**
- ✅ **1+ owner**
- ✅ **15+ character description**

**Incidents:** None

---

## 📊 BI & Analytics Governance

### Rule 8: Dashboard Governance

**Purpose:** Ensure BI dashboards have proper documentation

**Applies to:**
- Dashboards from: Looker, Tableau, Superset, PowerBI, Mode

**Requirements:**
- ✅ **1+ owner**
- ✅ **30+ character description**

**Incidents:** None

**Use Case:** Executive dashboards, team reports, KPI tracking

---

### Rule 9: Chart Governance

**Purpose:** Charts and visualizations should have owners

**Applies to:**
- Charts from: Looker, Tableau, Superset, PowerBI, Mode

**Requirements:**
- ✅ **1+ owner**
- ✅ **20+ character description**

**Incidents:** None

---

## ✨ Data Quality Governance

### Rule 10: Certified Data Governance

**Purpose:** Enhanced requirements for certified/validated datasets

**Applies to:**
- Datasets tagged with: `Certified`, `Validated`, or `DataQuality`

**Requirements:**
- ✅ **1+ owner** (DATAOWNER or TECHNICAL_OWNER)
- ✅ **50+ character description**
- ✅ **Data quality glossary term** (one of):
  - DataQuality.Validated
  - DataQuality.Certified
  - DataQuality.MonitoringEnabled

**Incidents:** None

**Use Case:** Golden datasets, certified analytics tables, validated ML features

---

## ⚙️ Pipeline Governance

### Rule 11: Critical Data Pipeline Governance (MEDIUM Priority)

**Purpose:** Production pipelines processing tier-1 data need governance

**Applies to:**
- DATA_JOB and DATA_FLOW entities
- PROD environment
- Tagged with: `Critical` or `tier:1`

**Requirements:**
- ✅ **1+ owner** (DATAOWNER or TECHNICAL_OWNER)
- ✅ **50+ character description**

**Incidents:** Creates MEDIUM priority incidents assigned to data-engineering-team

**Use Case:** Critical ETL jobs, tier-1 data pipelines, revenue-impacting workflows

---

## 🔧 Development & Lifecycle

### Rule 12: Development Dataset Governance (LIGHT)

**Purpose:** Lighter requirements for non-production environments

**Applies to:**
- Datasets in DEV, QA, or STAGING environments

**Requirements:**
- ✅ **1+ owner** (any type)

**Incidents:** None

**Use Case:** Development tables, test data, staging environments

---

### Rule 13: Deprecated Dataset Tracking

**Purpose:** Ensure deprecated assets are properly documented

**Applies to:**
- Datasets and dashboards tagged with: `Deprecated` or `Sunset`

**Requirements:**
- ✅ **1+ owner**
- ✅ **30+ character description** (should explain deprecation)

**Incidents:** None

**Use Case:** Legacy tables being phased out, deprecated dashboards

---

## 🏷️ Required Tags & Terms Reference

### Data Classification Glossary Terms

Create these in DataHub UI under **Glossary**:

```
Classification.PII
Classification.Sensitive
Classification.Financial
Classification.Public
Classification.Internal
Classification.Confidential
Classification.Restricted

DataQuality.Validated
DataQuality.Certified
DataQuality.MonitoringEnabled

Compliance.GDPR
Compliance.CCPA
Compliance.HIPAA
Compliance.SOX
Compliance.PCI
```

### Compliance & Classification Tags

Create these in DataHub UI under **Tags**:

**Tier Classification:**
- `tier:1` / `Tier1` / `Critical`
- `tier:2` / `Tier2`
- `tier:3` / `Tier3`

**Compliance:**
- `GDPR`, `CCPA`, `HIPAA`, `SOX`, `PCI`
- `ComplianceReviewed`, `AuditReviewed`

**Data Sensitivity:**
- `PII`, `PersonalData`, `IdentifiableData`
- `Sensitive`, `Confidential`, `Restricted`
- `Financial`, `FinancialReporting`

**Access Control:**
- `AccessControlled`, `RestrictedUse`

**Data Quality:**
- `Validated`, `Approved`, `Certified`, `DataQuality`

**Lifecycle:**
- `Deprecated`, `Sunset`

---

## 📋 How to Use This System

### For Data Producers

1. **Tag your datasets appropriately:**
   ```python
   # Example: Mark a dataset as PII
   tags = GlobalTagsClass(tags=[
       TagAssociationClass(tag="urn:li:tag:PII"),
       TagAssociationClass(tag="urn:li:tag:GDPR")
   ])
   ```

2. **Add owners:**
   - Navigate to dataset in DataHub UI
   - Click "Add Owners"
   - Select DATAOWNER or TECHNICAL_OWNER type

3. **Add descriptions:**
   - Click "Edit" on dataset
   - Provide meaningful description (follow min length requirements)

4. **Add glossary terms for classification:**
   - Click "Add Terms"
   - Select appropriate classification term

### For Data Consumers

1. **Check Governance tab** on datasets
   - See which governance rules pass/fail
   - Understand compliance status
   - View test results

2. **Filter by governance status:**
   - Use search filters to find compliant datasets
   - Identify datasets needing attention

### For Data Governance Team

1. **Monitor incidents:**
   - Navigate to Incidents page
   - Filter by priority (CRITICAL, HIGH, MEDIUM)
   - Filter by type (PII_GOVERNANCE_VIOLATION, etc.)

2. **Track compliance:**
   - Run reports on governance pass/fail rates
   - Identify datasets needing classification
   - Track improvement over time

3. **Adjust rules:**
   - Edit `governance-rules.yml`
   - Adjust min_owners, min_length, required tags
   - Restart datahub-actions container

---

## 🔄 Testing Governance Rules

### Test a Specific Dataset

```bash
# Re-ingest or update the dataset to trigger governance
python trigger_with_system_auth.py
```

### Monitor Governance Processing

```bash
# Watch governance checks in real-time
docker logs datahub-datahub-actions-1 -f | grep -i governance
```

### Check Results in UI

1. Navigate to dataset in DataHub
2. Click **Governance** tab
3. View test results for all applicable rules

---

## 🎯 Progressive Governance Strategy

### Phase 1: Foundation (Week 1-2)
- ✅ Enable Rule 5 (Production Dataset Governance)
- ✅ Enable Rule 6 (Snowflake Governance)
- Focus: Get all production datasets with basic owners + descriptions

### Phase 2: Compliance (Week 3-4)
- ✅ Enable Rule 2 (PII Governance)
- ✅ Enable Rule 3 (Financial Governance)
- Focus: Tag and classify sensitive data

### Phase 3: Tiering (Week 5-6)
- ✅ Enable Rule 1 (Tier 1 Governance)
- Focus: Identify and tag critical datasets

### Phase 4: Quality (Week 7-8)
- ✅ Enable Rule 10 (Certified Data)
- Focus: Certify golden datasets

### Phase 5: Full Coverage (Week 9+)
- ✅ Enable all remaining rules
- Focus: Dashboards, charts, pipelines, dev environments

---

## 🚨 Troubleshooting

### Rule Not Triggering

1. **Check logs:**
   ```bash
   docker logs datahub-datahub-actions-1 --tail 100 | grep "Processing entity"
   ```

2. **Verify aspect filter:**
   - Ensure `status`, `schemaMetadata`, or `datasetProperties` is in governance-action-config.yaml

3. **Check scope:**
   - Verify entity type, platform, environment, and tags match rule scope

### Incidents Not Created

1. **Check `create_incident_on_fail`:** Should be `true`
2. **Verify incident_config:** Ensure priority and assignees are valid
3. **Check permissions:** Ensure governance bot has rights to create incidents

### Rules Not Loading

```bash
# Check rule count in logs
docker logs datahub-datahub-actions-1 | grep "Loaded.*rules"

# Should show: "Loaded 13 governance rules"
```

---

## 📚 Additional Resources

- **DataHub Docs:** https://datahubproject.io/docs/governance
- **Acryl Governance:** https://www.acryldata.io/
- **Rule Examples:** `datahub-actions/examples/governance/rules.yml`
- **Check Implementations:** `datahub-actions/src/datahub_actions/plugin/action/governance/checks/`

---

## Summary

You now have a **production-ready governance framework** with:
- ✅ 13 comprehensive rules
- ✅ 4 severity levels (CRITICAL, HIGH, MEDIUM, STANDARD)
- ✅ Coverage across datasets, dashboards, charts, and pipelines
- ✅ Compliance rules for PII, Financial, and Sensitive data
- ✅ Automated incident creation for violations
- ✅ Progressive governance strategy

All rules are actively monitoring your data catalog and will trigger on every ingestion!
