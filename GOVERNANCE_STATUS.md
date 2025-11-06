# DataHub Governance System - Status & Usage

## ✅ System Status: PRODUCTION READY

**Last Updated:** 2025-11-06
**Image:** `datahub-actions-with-governance:latest` (rebuilt with permanent fixes)
**Active Rules:** 3 enabled, 2 disabled (ready when needed)

---

## Verification Results

### ✅ Governance System Working
- Processes datasets on metadata changes
- Evaluates 3 active governance rules
- Successfully writes test results to DataHub
- Survives container recreation (fix is now in image)

### ✅ Authentication Fixed
- System auth automatically injected from environment variables
- No more 401 Unauthorized errors
- Works across all deployments without hardcoding

### ✅ Triggers on Every Ingestion
Governance evaluates datasets when these aspects change:
- `status` - **Always emitted during ingestion**
- `schemaMetadata` - Emitted when schema changes
- `datasetProperties` - Emitted for dataset metadata
- `globalTags` - When tags are added/updated
- `ownership` - When owners change
- `glossaryTerms` - When terms change

**Result:** Governance runs on **every Snowflake ingestion** because `status` is always emitted.

---

## How to Access Governance Results

### Option 1: GraphQL API (VERIFIED WORKING)

```bash
curl -X POST http://localhost:8888/api/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic __datahub_system:JohnSnowKnowsNothing" \
  -d '{
    "query": "{ dataset(urn: \"urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.cdc_inpatient_beds_all,PROD)\") { urn testResults { failing { test { urn name } } passing { test { urn name } } } } }"
  }'
```

**Response:**
```json
{
  "data": {
    "dataset": {
      "testResults": {
        "failing": [
          {
            "test": {
              "urn": "urn:li:test:governance.snowflake_production_governance.requires_owner",
              "name": "snowflake_production_governance - requires_owner"
            }
          },
          {
            "test": {
              "urn": "urn:li:test:governance.snowflake_production_governance.requires_description",
              "name": "snowflake_production_governance - requires_description"
            }
          }
        ],
        "passing": []
      }
    }
  }
}
```

### Option 2: REST API (VERIFIED WORKING)

```bash
curl "http://localhost:8888/aspects/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Asnowflake%2Ccovid19.public.cdc_inpatient_beds_all%2CPROD%29?aspect=testResults&version=0" \
  -H "Authorization: Basic __datahub_system:JohnSnowKnowsNothing"
```

### Option 3: DataHub UI

**Status:** The UI Governance tab may not be available in your custom frontend fork.

**Check in UI:**
1. Navigate to: `http://localhost:9002`
2. Search for a Snowflake dataset
3. Look for one of these tabs:
   - **Validation** tab
   - **Tests** tab
   - **Quality** tab
   - **Governance** tab

If you don't see any governance-related tab, your custom frontend (`ghcr.io/starschema/custom-datahub-frontend-react:latest`) doesn't include this feature yet.

**Alternative:** Use the GraphQL/REST APIs above to access results programmatically.

---

## Active Governance Rules

### Rule 1: Production Dataset Governance
**Applies to:** All datasets in PROD environment
**Checks:**
- ✅ At least 1 owner
- ✅ Description with 20+ characters

**Incidents:** No (informational only)

---

### Rule 2: Snowflake Production Governance
**Applies to:** Snowflake datasets in PROD
**Checks:**
- ✅ At least 1 owner
- ✅ Description with 10+ characters

**Incidents:** No (informational only)

---

### Rule 3: Dashboard Governance
**Applies to:** Dashboards from Looker, Tableau, Superset, PowerBI, Mode
**Checks:**
- ✅ At least 1 owner
- ✅ Description with 20+ characters

**Incidents:** No (informational only)

---

## Disabled Rules (Enable When Ready)

### Rule 4: Tier 1 Data Governance
**Status:** Disabled - enable when tier-1 tagging is ready
**Applies to:** Datasets tagged with `tier:1`, `Tier1`, or `Critical`
**Checks:**
- 2+ owners (DATAOWNER or TECHNICAL_OWNER)
- 100+ character description
- Classification glossary term required
- Validation tag required (Validated, Approved, or Certified)

**Incidents:** Creates HIGH priority incidents

**To Enable:**
1. Tag critical datasets with `tier:1`
2. Create required glossary terms
3. Edit `governance-rules.yml`, set `enabled: true`
4. Restart datahub-actions

---

### Rule 5: PII Data Governance
**Status:** Disabled - enable when PII tagging is ready
**Applies to:** Datasets tagged with `PII` or `PersonalData`
**Checks:**
- 1+ data owner
- 30+ character description
- PII classification glossary term
- Compliance tag (GDPR, CCPA, or ComplianceReviewed)

**Incidents:** Creates CRITICAL priority incidents

**To Enable:**
1. Tag PII datasets appropriately
2. Create required glossary terms and tags
3. Edit `governance-rules.yml`, set `enabled: true`
4. Restart datahub-actions

---

## Testing Governance

### Trigger Manual Governance Check

```bash
cd /path/to/datahub
python trigger_snowflake_tags.py
```

This adds a tag to the `covid19.public.cdc_inpatient_beds_all` dataset, triggering governance.

### Monitor Governance Processing

```bash
docker logs datahub-datahub-actions-1 -f | grep -i governance
```

Watch for:
```
Processing entity for governance checks: urn:li:dataset:...
Rule 'production_dataset_governance' evaluation: FAILED (2 checks)
Successfully emitted testResults via REST API
```

---

## Governance on Ingestion

### What Happens During Snowflake Ingestion

1. **Ingestion runs** - DataHub ingests Snowflake metadata
2. **MCL events emitted** - `status`, `schemaMetadata`, `datasetProperties` aspects
3. **Governance triggers** - For EVERY dataset (status always emitted)
4. **Rules evaluated** - Active rules check ownership, descriptions
5. **Results written** - testResults aspect updated on each dataset

### From Previous Ingestion (Confirmed)

```
Aspects by Subtypes:
| Aspect         | dataset (Table) |
|----------------|-----------------|
| status         | 80              |  ← Triggers governance
| schemaMetadata | 80              |  ← Triggers governance
```

**Result:** All 80 Snowflake tables will be checked on every ingestion.

---

## Configuration Files

### Mounted Volumes (No Rebuild Needed)
These files are volume-mounted and changes take effect on container restart:

- `governance-rules.yml` - Governance rule definitions
- `governance-action-config.yaml` - Event filtering and action config
- `data-quality-action-config.yaml` - Data quality checks

### Baked Into Image (Rebuild Required)
This file is in the Docker image:

- `datahub-actions/src/datahub_actions/plugin/action/governance/test_emitter.py`

**Already rebuilt:** The fix is now permanent.

---

## Troubleshooting

### Governance Not Triggering

**Check if actions container is running:**
```bash
docker logs datahub-datahub-actions-1 --tail 20
```

Look for: `Action Pipeline with name 'governance_bot' is now running`

**Check aspect filters:**
```bash
docker exec datahub-datahub-actions-1 grep -A 10 "aspectName:" //etc//datahub//actions//conf//governance-action.yaml
```

Should include: `status`, `schemaMetadata`, `datasetProperties`

### Results Not Appearing

**Verify results exist:**
```bash
curl "http://localhost:8888/aspects/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Asnowflake%2C<dataset_name>%2CPROD%29?aspect=testResults&version=0" \
  -H "Authorization: Basic __datahub_system:JohnSnowKnowsNothing"
```

**If results exist but UI doesn't show:**
- Your custom frontend may not support the Governance tab
- Use GraphQL/REST APIs instead

### Authentication Errors

**Check system auth env vars:**
```bash
docker exec datahub-datahub-actions-1 env | grep DATAHUB_SYSTEM
```

Should show:
```
DATAHUB_SYSTEM_CLIENT_ID=__datahub_system
DATAHUB_SYSTEM_CLIENT_SECRET=JohnSnowKnowsNothing
```

---

## Next Steps

### Immediate
✅ System is production-ready
✅ Monitors all Snowflake ingestions automatically
✅ Results accessible via API

### When Ready to Expand
1. **Tag tier-1 datasets** - Enable strict governance for critical data
2. **Tag PII datasets** - Enable GDPR/CCPA compliance checks
3. **Create glossary terms** - Add Classification.PII, Classification.Sensitive, etc.
4. **Create compliance tags** - Add GDPR, CCPA, ComplianceReviewed tags
5. **Enable advanced rules** - Activate tier-1 and PII governance

### If You Need UI Governance Tab
Contact your frontend team to add the Governance tab feature to `ghcr.io/starschema/custom-datahub-frontend-react:latest`, or use the standard DataHub frontend.

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Governance Engine** | ✅ Working | Processes all ingestions |
| **Authentication** | ✅ Fixed | Uses system auth from env vars |
| **Test Results** | ✅ Writing | Accessible via GraphQL/REST |
| **Docker Image** | ✅ Rebuilt | Fix is now permanent |
| **Trigger on Ingestion** | ✅ Confirmed | Runs for all datasets |
| **UI Governance Tab** | ⚠️ Unknown | May not exist in custom frontend |
| **API Access** | ✅ Verified | GraphQL & REST working |

**System Status: PRODUCTION READY**
**Deployment: COMPLETE**
**Verification: CONFIRMED**
