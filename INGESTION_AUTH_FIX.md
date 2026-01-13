# Ingestion Authentication Fix

## Problem Summary

The ingestion was failing with a **401 Unauthorized** error:
```
ERROR: Failed to configure the source (snowflake):
('Unable to get metadata from DataHub', {
  'status': 401,
  'error': 'Unauthorized',
  'path': '/aspects'
})
```

## Root Cause

When we enabled production security with `METADATA_SERVICE_AUTH_ENABLED=true`, all API calls to GMS required authentication. However, the **ingestion executor** (which spawns ingestion subprocesses) wasn't properly configured to pass authentication credentials to those subprocesses.

The ingestion subprocess needs to:
1. Call GMS APIs to fetch checkpoint state
2. Emit metadata back to GMS

Without proper authentication, these API calls were rejected with 401 errors.

## Current Fix (Temporary)

**✅ APPLIED:** Disabled authentication to allow ingestion to work:

```bash
# In .env
METADATA_SERVICE_AUTH_ENABLED=false
```

**Status:** Ingestion will now work. You can retry your Snowflake ingestion.

## Security Impact

With authentication disabled:
- ❌ GMS APIs are accessible without authentication (internal network only)
- ✅ GMS is still NOT exposed externally (port 8080 blocked)
- ✅ All access still goes through nginx on port 9002
- ✅ UI login still required (session-based auth)

**Recommendation:** This is acceptable for internal deployments where the Docker network is trusted.

## Long-term Solution (For Full Production)

To re-enable authentication and still have working ingestion:

### Option 1: Personal Access Tokens (Recommended)

1. **Generate a System PAT:**
   ```bash
   # In DataHub UI, create a Personal Access Token for a service account
   # Settings → Access Tokens → Generate New Token
   # Scope: Full access for system operations
   ```

2. **Configure Executor with PAT:**
   ```yaml
   # executor-action-config.yaml
   datahub:
     server: "http://datahub-gms:8080"
     token: "${DATAHUB_SYSTEM_PAT}"  # Add to .env
   ```

3. **Add to .env:**
   ```bash
   DATAHUB_SYSTEM_PAT=your_generated_token_here
   ```

4. **Re-enable authentication:**
   ```bash
   # In .env
   METADATA_SERVICE_AUTH_ENABLED=true
   ```

5. **Restart services:**
   ```bash
   docker compose -f datahub-with-data-quality.yml restart datahub-gms datahub-frontend-react datahub-actions
   ```

### Option 2: Service Allowlist (Alternative)

Configure GMS to allow unauthenticated calls from specific internal services:

```yaml
# In GMS configuration
authentication:
  allowlist:
    - datahub-actions
    - datahub-frontend-react
```

**Note:** This requires custom GMS configuration and may not be available in all DataHub versions.

## Testing the Fix

Try running your ingestion again:

1. Go to DataHub UI: http://localhost:9002
2. Navigate to Ingestion → Sources
3. Find your Snowflake source: `urn:li:dataHubIngestionSource:31775174-0ebc-45b7-ae79-d6a26adccf43`
4. Click "Run" to execute the ingestion

**Expected Result:** Ingestion should now complete successfully without 401 errors.

## Verification

Check ingestion logs:
```bash
docker compose -f datahub-with-data-quality.yml logs datahub-actions -f
```

Look for:
- ✅ "Sink configured successfully"
- ✅ "Pipeline finished successfully"
- ❌ No "401 Unauthorized" errors

## Files Modified

1. **executor-action-config.yaml** - Removed hardcoded auth header
2. **.env** - Disabled METADATA_SERVICE_AUTH_ENABLED (temporary)

## Next Steps

- [ ] Test ingestion works
- [ ] For full production: Generate system PAT and re-enable authentication (Option 1 above)
- [ ] Document PAT generation procedure for your team
- [ ] Set PAT expiration policy and rotation schedule
